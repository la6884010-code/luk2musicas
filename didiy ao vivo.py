import pygame
import moderngl
import numpy as np
import pyaudio
import threading
import queue
from collections import deque

# --- Parâmetros ---
WIN_SIZE = (1280, 720)
CHUNK = 1024

HELP = """
╔══════════════════════════════════════════════════════════╗
║         FRACTAL VISUALIZER — ELITE  v3.0                ║
╠══════════════════════════════════════════════════════════╣
║  P / ←→     Trocar paleta (5 paletas)                   ║
║  M          Trocar modo fractal (4 modos)                ║
║  V / ↑↓     Ajustar vinheta                             ║
║  G          Toggle glow (pós-processamento)              ║
║  F          Toggle feedback de frame                     ║
║  B          Toggle sincronização com BPM                 ║
║  [ / ]      Sensibilidade de beat ( - / + )             ║
║  +/-        Velocidade de viagem no fractal              ║
║  SPACE      Freeze / unfreeze áudio                      ║
║  ESC        Sair                                         ║
╠══════════════════════════════════════════════════════════╣
║  HUD mostra: Modo · Paleta · BPM · Graves/Médios/Agudos ║
╚══════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════
#  DEVICE DISCOVERY
# ══════════════════════════════════════════════════════════════════
def find_loopback_device(p):
    print("\n── Dispositivos de áudio disponíveis ──")
    best = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info['name'].lower()
        max_in = info['maxInputChannels']
        print(f"  [{i}] {info['name']}  (entradas: {max_in})")
        if max_in > 0:
            if 'loopback' in name:
                best = (i, info, 'WASAPI Loopback')
                break
            if any(x in name for x in ['stereo mix', 'mix estéreo', 'mistura estéreo', 'wave out']):
                best = (i, info, 'Stereo Mix')
    if best:
        idx, info, tipo = best
        rate = int(info['defaultSampleRate'])
        print(f"\n✔ Capturando via: [{idx}] {info['name']} ({tipo})\n")
        return idx, rate
    else:
        print("\n⚠  Nenhum loopback encontrado — usando microfone padrão.\n")
        return None, 44100


# ══════════════════════════════════════════════════════════════════
#  AUDIO ANALYZER — thread separada com fila (fix do travamento)
# ══════════════════════════════════════════════════════════════════
class AudioAnalyzer:
    def __init__(self):
        self.p = pyaudio.PyAudio()

        # Estado suavizado
        self.smooth_audio = 0.0
        self.smooth_bass  = 0.0
        self.smooth_mid   = 0.0
        self.smooth_high  = 0.0

        # Normalização adaptativa independente por banda (decay 0.995)
        self.bass_max  = 1e-6
        self.mid_max   = 1e-6
        self.high_max  = 1e-6

        # Beat detection — spectral flux
        self.flux_history    = deque(maxlen=43)
        self.beat_cool       = 0
        self.beat_flash      = 0.0
        self.bpm_sync        = True
        self.beat_sensitivity = 1.5   # multiplica variância no threshold

        # BPM estimado
        self._beat_times = deque(maxlen=8)
        self.bpm         = 0.0

        # Spectral flux: frame anterior da FFT
        self.prev_fft     = None
        self.flux_smooth  = 0.0    # flux suavizado (anti-jitter)
        self.flux_peak    = 0.0    # pico decaente — calculado na thread, sem travar
        self.silence      = True   # detector de silêncio
        self.energy_floor = 0.001  # gate mínimo de energia no grave

        # Fila thread-safe — resolve o overflow/travamento
        self._q       = queue.Queue(maxsize=4)
        self._running = True

        device_index, self._rate = find_loopback_device(self.p)

        try:
            kwargs = dict(format=pyaudio.paInt16, channels=1, rate=self._rate,
                          input=True, frames_per_buffer=CHUNK)
            if device_index is not None:
                kwargs['input_device_index'] = device_index
            self._stream = self.p.open(**kwargs)
            print("✔ Stream aberto.\n")
        except OSError as e:
            print(f"✘ Erro: {e} — tentando padrão...")
            self._rate = 44100
            self._stream = self.p.open(
                format=pyaudio.paInt16, channels=1, rate=44100,
                input=True, frames_per_buffer=CHUNK)

        # Pré-calcula índices FFT das bandas — feito APÓS saber self._rate
        freqs = np.fft.rfftfreq(CHUNK, 1.0 / self._rate)
        self.bass_idx = np.where((freqs >= 20)   & (freqs < 140))[0]   # kick puro (corta guitarra grave)
        self.mid_idx  = np.where((freqs >= 140)  & (freqs < 4000))[0]
        self.high_idx = np.where((freqs >= 4000) & (freqs < 20000))[0]

        # Cooldown proporcional ao tempo real (~300ms — evita metralhadora)
        self._cool_frames = max(8, int(0.30 * self._rate / CHUNK))

        # Thread de leitura — nunca bloqueia o render
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    # ── Thread de leitura ──────────────────────────────────────────
    def _read_loop(self):
        while self._running:
            try:
                raw  = self._stream.read(CHUNK, exception_on_overflow=False)
                data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

                # FFT
                fft = np.abs(np.fft.rfft(data * np.hanning(len(data))))

                # Bandas usando índices pré-calculados
                def band_rms(idx):
                    if len(idx) == 0:
                        return 0.0
                    return float(np.sqrt(np.mean(fft[idx] ** 2)))

                bass = band_rms(self.bass_idx)
                mid  = band_rms(self.mid_idx)
                high = band_rms(self.high_idx)
                peak = float(np.max(np.abs(data)))

                # Spectral flux focado no kick (20-140Hz)
                # Detecta transiente de energia no grave, ignora sustain/vocal
                if self.prev_fft is None:
                    flux = 0.0
                else:
                    diff = fft[self.bass_idx] - self.prev_fft[self.bass_idx]
                    flux = float(np.sum(np.maximum(diff, 0.0)))  # só aumentos
                self.prev_fft = fft.copy()

                # Suavização exponencial do flux — remove jitter frame a frame
                self.flux_smooth = 0.3 * flux + 0.7 * self.flux_smooth
                flux = self.flux_smooth

                # Pico decaente — atualizado na thread, zero custo no loop principal
                self.flux_peak = max(self.flux_peak * 0.98, flux)

                # Detector de silêncio — energia total da FFT
                total_energy = float(np.sum(fft))
                self.silence = total_energy < 1e-5

                # Descarta frames antigos se a fila estiver cheia
                if self._q.full():
                    try:
                        self._q.get_nowait()
                    except queue.Empty:
                        pass

                self._q.put_nowait((peak, bass, mid, high, flux))

            except OSError:
                pass   # stream resetado ou troca de música — continua

    # ── Chamado pelo loop principal (não bloqueia) ─────────────────
    def get_val(self):
        try:
            peak, bass, mid, high, flux = self._q.get_nowait()
        except queue.Empty:
            peak = self.smooth_audio
            bass = self.smooth_bass
            mid  = self.smooth_mid
            high = self.smooth_high
            flux = 0.0

        # Noise gate
        if peak < 0.025:
            peak = 0.0

        def smooth(old, new, up=0.35, dn=0.08):
            a = up if new > old else dn
            return old + (new - old) * a

        # Normalização adaptativa independente por banda
        # Cada banda responde ao próprio histórico — não brigam entre si
        self.bass_max = max(self.bass_max * 0.995, bass)
        self.mid_max  = max(self.mid_max  * 0.995, mid)
        self.high_max = max(self.high_max * 0.995, high)

        bass_n = min(bass / (self.bass_max + 1e-6), 1.0)
        mid_n  = min(mid  / (self.mid_max  + 1e-6), 1.0)
        high_n = min(high / (self.high_max + 1e-6), 1.0)

        self.smooth_audio = smooth(self.smooth_audio, min(peak, 1.0))
        self.smooth_bass  = smooth(self.smooth_bass,  bass_n, 0.4, 0.06)
        self.smooth_mid   = smooth(self.smooth_mid,   mid_n,  0.3, 0.07)
        self.smooth_high  = smooth(self.smooth_high,  high_n, 0.5, 0.10)

        val = float(np.clip(self.smooth_audio, 0.0, 1.0))

        # ── Beat detection via spectral flux com adaptive threshold ──
        # Detecta transiente de energia no grave (kick), não pico geral
        beat = False
        if self.bpm_sync and not self.silence:
            self.flux_history.append(flux)

            if len(self.flux_history) > 10:
                avg = float(np.mean(self.flux_history))
                var = float(np.var(self.flux_history))

                # Threshold adaptativo com piso relativo
                # Evita colapso quando energia cai entre músicas
                threshold = avg + var * self.beat_sensitivity
                threshold = max(threshold, avg * 1.5)

                # Gate de energia mínima no grave — música calma não dispara
                energy_ok  = bass_n > 0.08
                # Só dispara no pico dominante do kick, não nos resíduos
                is_peak    = flux >= self.flux_peak * 0.95

                if flux > threshold and energy_ok and is_peak and self.beat_cool <= 0:
                    beat = True
                    self.beat_cool = self._cool_frames
                    now = pygame.time.get_ticks() / 1000.0
                    self._beat_times.append(now)
                    if len(self._beat_times) >= 2:
                        intervals = np.diff(list(self._beat_times))
                        self.bpm = round(60.0 / float(np.mean(intervals)))

            if self.beat_cool > 0:
                self.beat_cool -= 1

        if beat:
            self.beat_flash = 1.0
        else:
            self.beat_flash *= 0.82

        return (
            val,
            float(self.beat_flash),
            float(self.smooth_bass),
            float(self.smooth_mid),
            float(self.smooth_high),
        )

    def close(self):
        self._running = False
        self._thread.join(timeout=1.0)
        self._stream.stop_stream()
        self._stream.close()
        self.p.terminate()


# ══════════════════════════════════════════════════════════════════
#  SHADERS
# ══════════════════════════════════════════════════════════════════
VERTEX_SHADER = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330
in  vec2 v_uv;
out vec4 f_color;

uniform float u_time;
uniform vec2  u_res;
uniform float u_audio;
uniform float u_beat;
uniform float u_bass;
uniform float u_mid;
uniform float u_high;
uniform float u_color_offset;   // offset automático girado pelo beat
uniform int   u_palette;
uniform int   u_mode;
uniform float u_vignette;
uniform float u_travel;
uniform bool  u_glow;
uniform bool  u_feedback;
uniform sampler2D u_prev;

// ── ACES ──────────────────────────────────────────────────────────
vec3 aces(vec3 x) {
    return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0);
}

// ── Paletas com offset de cor automático ──────────────────────────
//    t         → posição no ciclo de cor (0..1)
//    co        → color_offset (desliza no beat)
//    intensity → u_audio para escalar saturação
vec3 palette(float t, float co, float intensity) {
    t += co;   // offset girado pelo beat — faz a cor "dançar"
    vec3 a, b, c, d;

    if (u_palette == 0) { // Gelo → Fogo
        float fire = smoothstep(0.05, 0.6, intensity * 3.0) + u_beat * 0.4;
        a = mix(vec3(0.5,0.5,0.5), vec3(0.5,0.3,0.1), fire);
        b = mix(vec3(0.5,0.5,0.5), vec3(0.5,0.4,0.1), fire);
        c = mix(vec3(1.0,1.0,1.0), vec3(1.0,0.7,0.0), fire);
        d = mix(vec3(0.30,0.45,0.60), vec3(0.00,0.10,0.20), fire);
    }
    else if (u_palette == 1) { // Neon
        // Saturação cresce com graves
        b = vec3(0.5 + u_bass * 0.3, 0.5, 0.0) ;
        a = vec3(0.5, 0.0, 0.5 + u_high * 0.3);
        c = vec3(1.0, 1.0, 1.0);
        d = vec3(0.00, 0.33, 0.67);
    }
    else if (u_palette == 2) { // Pastel
        a = vec3(0.8, 0.7 + u_mid * 0.2, 0.9);
        b = vec3(0.2, 0.3, 0.2 + u_high * 0.3);
        c = vec3(1.0, 0.8, 0.9);
        d = vec3(0.10, 0.40, 0.20);
    }
    else if (u_palette == 3) { // Psicodélica
        a = vec3(0.5, 0.5, 0.5);
        b = vec3(0.5 + u_bass * 0.3, 0.5, 0.5 + u_high * 0.3);
        c = vec3(2.0, 1.0 + u_mid, 0.0);
        d = vec3(0.50, 0.20, 0.25);
    }
    else { // Aurora boreal
        a = vec3(0.0, 0.5 + u_bass * 0.2, 0.4);
        b = vec3(0.1, 0.4, 0.3 + u_high * 0.2);
        c = vec3(0.5, 1.0, 0.8);
        d = vec3(0.00, 0.15, 0.50);
    }

    // Saturação extra conforme intensidade geral
    b *= 1.0 + intensity * 0.5;

    return a + b * cos(6.28318 * (c * t + d));
}

vec2 rot2(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(p.x*c - p.y*s, p.x*s + p.y*c);
}

// Macro conveniente — usa u_color_offset e u_audio automaticamente
#define PAL(t) palette(t, u_color_offset, u_audio)

// ── Modo 0: Loop fractal ──────────────────────────────────────────
vec3 modeLoop(vec2 uv0) {
    vec2 uv = uv0;
    // Graves → zoom, agudos → rotação extra
    uv *= 1.0 + u_bass * 0.6 + u_beat * 0.15;

    vec3 col = vec3(0.0);
    for (float i = 0.0; i < 4.0; i++) {
        uv = fract(uv * 1.5) - 0.5;
        uv = rot2(uv, u_time * 0.1 + i * 0.5 + u_mid * 0.8 + u_beat * 1.2 + u_high * 0.4);
        float d = length(uv);
        d = sin(d * 8.0 + u_time + i) / 8.0;
        d = abs(d);
        float b = pow(0.01 / (d + 0.0001), 0.8);
        float t = length(uv0) + i * 0.4 + u_time * 0.05;
        col += PAL(t) * b;
    }
    return col / 4.0;
}

// ── Modo 1: Tunnel ────────────────────────────────────────────────
vec3 modeTunnel(vec2 uv0) {
    float r = length(uv0);
    float a = atan(uv0.y, uv0.x);
    float depth = u_time * u_travel + u_beat * 0.3 + u_bass * 0.2;

    vec2 tuv = vec2(a / 6.28318, 0.3 / (r + 0.05) + depth);
    tuv += u_mid * 0.1;

    vec3 col = vec3(0.0);
    for (float i = 0.0; i < 3.0; i++) {
        tuv = fract(tuv * 1.4 + i * 0.1) - 0.5;
        float d = length(tuv);
        d = sin(d * 10.0 + u_time * 1.5) / 10.0;
        d = abs(d);
        float b = pow(0.008 / (d + 0.0001), 0.9);
        col += PAL(r + i * 0.3 + u_time * 0.04) * b;
    }
    col *= smoothstep(0.05, 0.25, r);
    return col / 3.0;
}

// ── Modo 2: Caleidoscópio ─────────────────────────────────────────
vec3 modeKaleid(vec2 uv0) {
    float SIDES = 6.0 + floor(u_beat * 4.0);
    float a = atan(uv0.y, uv0.x);
    float r = length(uv0);

    a = mod(a, 6.28318 / SIDES);
    a = abs(a - 3.14159 / SIDES);
    vec2 uv = vec2(cos(a), sin(a)) * r;

    uv *= 1.0 + u_bass * 0.4 + u_beat * 0.1;
    vec3 col = vec3(0.0);
    for (float i = 0.0; i < 4.0; i++) {
        uv = fract(uv * 1.5) - 0.5;
        uv = rot2(uv, u_time * 0.08 + i * 0.8 + u_high * 0.5);
        float d = length(uv);
        d = sin(d * 9.0 + u_time * 0.8) / 9.0;
        d = abs(d);
        float b = pow(0.01 / (d + 0.0001), 0.85);
        col += PAL(r + i * 0.5 + u_time * 0.06) * b;
    }
    return col / 4.0;
}

// ── Modo 3: Plasma orgânico ───────────────────────────────────────
vec3 modePlasma(vec2 uv0) {
    vec2 uv = uv0 * (2.0 + u_bass * 1.5);
    float t = u_time * 0.5;

    float v = sin(uv.x * 3.0 + t);
    v += sin(uv.y * 2.5 + t * 1.3 + u_mid * 2.0);
    v += sin((uv.x + uv.y) * 2.0 + t * 0.8);
    v += sin(sqrt(uv.x*uv.x + uv.y*uv.y + 1.0) * 3.5 + t);
    v += u_beat * 2.0 * sin(length(uv) * 5.0 - t * 3.0);
    v += u_high * sin(uv.x * 8.0 + t * 2.0) * 0.5;

    v = v * 0.5 + 0.5;
    vec3 col = PAL(v + u_time * 0.05);

    for (float i = 0.0; i < 2.0; i++) {
        uv = rot2(uv, t * 0.1 + i + u_mid * 0.3);
        float d = abs(sin(length(uv) * 6.0 + t));
        col += PAL(d + i * 0.5) * 0.15 * u_bass;
    }
    return col;
}

// ── Glow embutido ─────────────────────────────────────────────────
vec3 applyGlow(vec3 base) {
    if (!u_glow) return base;
    vec3 glow = base * 0.4 * (8.0 * 0.4);
    return base + glow / 8.0 * (0.4 + u_beat * 0.6);
}

void main() {
    vec2 uv0 = (gl_FragCoord.xy * 2.0 - u_res) / u_res.y;

    // Distorção radial: graves pulsam para fora, agudos tremem
    uv0 += uv0 * u_beat  * 0.04 * sin(u_time * 8.0);
    uv0 += uv0 * u_high  * 0.015 * sin(u_time * 20.0 + uv0.x * 5.0);

    vec3 col;
    if      (u_mode == 0) col = modeLoop(uv0);
    else if (u_mode == 1) col = modeTunnel(uv0);
    else if (u_mode == 2) col = modeKaleid(uv0);
    else                  col = modePlasma(uv0);

    // ── Feedback ──────────────────────────────────────────────────
    if (u_feedback) {
        vec2 fbUV = v_uv - 0.5;
        fbUV = rot2(fbUV, 0.002 + u_beat * 0.005);
        fbUV *= 0.985 - u_bass * 0.005;
        fbUV += 0.5;
        vec3 prev = texture(u_prev, fbUV).rgb;
        col = mix(col, col + prev * 0.45, 0.55);
    }

    col = applyGlow(col);

    col /= max(1.0, length(col) * 0.5);
    col  = aces(col * 1.2);

    // Flash de beat com cor da paleta atual (offset incluso)
    col = mix(col, PAL(u_time * 0.1) * 1.5, u_beat * 0.14);

    // Vinheta
    float vig = smoothstep(u_vignette, u_vignette * 0.2, length(uv0));
    col *= vig;

    f_color = vec4(col, 1.0);
}
"""

GLOW_VERT = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

GLOW_FRAG = """
#version 330
in  vec2 v_uv;
out vec4 f_color;
uniform sampler2D u_tex;
uniform vec2      u_res;
uniform float     u_strength;
uniform vec2      u_dir;

void main() {
    vec2 texel = 1.0 / u_res;
    vec3 col = vec3(0.0);
    float weights[5] = float[](0.227, 0.194, 0.121, 0.054, 0.016);
    col += texture(u_tex, v_uv).rgb * weights[0];
    for (int i = 1; i < 5; i++) {
        vec2 off = u_dir * texel * float(i) * 3.0;
        col += texture(u_tex, v_uv + off).rgb * weights[i];
        col += texture(u_tex, v_uv - off).rgb * weights[i];
    }
    vec3 orig = texture(u_tex, v_uv).rgb;
    f_color = vec4(orig + col * u_strength, 1.0);
}
"""

COMPOSITE_FRAG = """
#version 330
in  vec2 v_uv;
out vec4 f_color;
uniform sampler2D u_base;
uniform sampler2D u_glow;
uniform float     u_mix;
void main() {
    vec3 base = texture(u_base, v_uv).rgb;
    vec3 glow = texture(u_glow, v_uv).rgb;
    f_color = vec4(mix(base, base + glow, u_mix), 1.0);
}
"""


def make_quad(ctx, prog):
    verts = np.array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1], dtype='f4')
    vbo = ctx.buffer(verts)
    return ctx.vertex_array(prog, [(vbo, '2f', 'in_vert')])


# ══════════════════════════════════════════════════════════════════
#  HUD
# ══════════════════════════════════════════════════════════════════
def draw_hud(surface, mode_idx, palette_idx, bpm, val, bass, mid, high,
             glow_on, feedback_on, bpm_sync, sensitivity):
    font = pygame.font.SysFont("Consolas", 15)
    W, H = surface.get_size()

    PALETTE_NAMES = ['Gelo/Fogo', 'Neon', 'Pastel', 'Psicodélica', 'Aurora']
    MODE_NAMES    = ['Loop Fractal', 'Tunnel', 'Caleidoscópio', 'Plasma']

    lines = [
        f"Modo:    {MODE_NAMES[mode_idx]}",
        f"Paleta:  {PALETTE_NAMES[palette_idx]}",
        f"BPM:     {int(bpm) if bpm > 0 else '---'}",
        f"Beat:    {'ON' if bpm_sync else 'OFF'}  Sens: {sensitivity:.1f}x",
        f"Glow:    {'ON' if glow_on else 'OFF'}",
        f"Feedback:{'ON' if feedback_on else 'OFF'}",
        "",
        f"▐{'█' * int(bass  * 12):12s}  Graves",
        f"▐{'█' * int(mid   * 12):12s}  Médios",
        f"▐{'█' * int(high  * 12):12s}  Agudos",
    ]

    pad = 10
    for i, line in enumerate(lines):
        shadow = font.render(line, True, (0, 0, 0))
        text   = font.render(line, True, (200, 220, 255))
        surface.blit(shadow, (pad + 1, pad + 1 + i * 18))
        surface.blit(text,   (pad,     pad     + i * 18))


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    print(HELP)

    pygame.init()
    pygame.display.set_caption("◈ Fractal Visualizer — Elite v3.0")
    screen = pygame.display.set_mode(WIN_SIZE, pygame.OPENGL | pygame.DOUBLEBUF)
    ctx    = moderngl.create_context()
    audio  = AudioAnalyzer()

    prog  = ctx.program(vertex_shader=VERTEX_SHADER,  fragment_shader=FRAGMENT_SHADER)
    gprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=GLOW_FRAG)
    cprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=COMPOSITE_FRAG)

    vao  = make_quad(ctx, prog)
    gvao = make_quad(ctx, gprog)
    cvao = make_quad(ctx, cprog)

    W, H = WIN_SIZE

    def make_fbo():
        tex = ctx.texture((W, H), 3, dtype='f4')
        tex.filter   = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = False
        tex.repeat_y = False
        return ctx.framebuffer([tex]), tex

    fbo_main,  tex_main  = make_fbo()
    fbo_prev,  tex_prev  = make_fbo()
    fbo_glowA, tex_glowA = make_fbo()
    fbo_glowB, tex_glowB = make_fbo()



    # ── Estado interativo ──────────────────────────────────────────
    palette_idx  = 0
    mode_idx     = 0
    vignette     = 1.5
    glow_on      = True
    feedback_on  = False
    travel_spd   = 0.3
    audio_freeze = False
    frozen_data  = (0.0, 0.0, 0.0, 0.0, 0.0)

    # Offset de cor automático (desliza no beat)
    color_offset      = 0.0
    color_offset_vel  = 0.0   # velocidade atual do offset

    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()

    PALETTE_NAMES = ['Gelo/Fogo', 'Neon', 'Pastel', 'Psicodélica', 'Aurora']
    MODE_NAMES    = ['Loop Fractal', 'Tunnel', 'Caleidoscópio', 'Plasma']

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_ESCAPE:
                        return
                    elif k in (pygame.K_p, pygame.K_RIGHT):
                        palette_idx = (palette_idx + 1) % 5
                        print(f"  🎨 Paleta → {PALETTE_NAMES[palette_idx]}")
                    elif k == pygame.K_LEFT:
                        palette_idx = (palette_idx - 1) % 5
                        print(f"  🎨 Paleta → {PALETTE_NAMES[palette_idx]}")
                    elif k == pygame.K_m:
                        mode_idx = (mode_idx + 1) % 4
                        print(f"  🔷 Modo → {MODE_NAMES[mode_idx]}")
                    elif k in (pygame.K_v, pygame.K_UP):
                        vignette = min(2.5, vignette + 0.1)
                        print(f"  🔆 Vinheta → {vignette:.1f}")
                    elif k == pygame.K_DOWN:
                        vignette = max(0.4, vignette - 0.1)
                        print(f"  🔆 Vinheta → {vignette:.1f}")
                    elif k == pygame.K_g:
                        glow_on = not glow_on
                        print(f"  ✨ Glow → {'ON' if glow_on else 'OFF'}")
                    elif k == pygame.K_f:
                        feedback_on = not feedback_on
                        print(f"  🔁 Feedback → {'ON' if feedback_on else 'OFF'}")
                    elif k == pygame.K_b:
                        audio.bpm_sync = not audio.bpm_sync
                        print(f"  🥁 BPM Sync → {'ON' if audio.bpm_sync else 'OFF'}")
                    elif k == pygame.K_RIGHTBRACKET:
                        audio.beat_sensitivity = min(3.0, audio.beat_sensitivity + 0.1)
                        print(f"  🎚 Sensibilidade → {audio.beat_sensitivity:.1f}x")
                    elif k == pygame.K_LEFTBRACKET:
                        audio.beat_sensitivity = max(1.1, audio.beat_sensitivity - 0.1)
                        print(f"  🎚 Sensibilidade → {audio.beat_sensitivity:.1f}x")
                    elif k in (pygame.K_PLUS, pygame.K_EQUALS):
                        travel_spd = min(2.0, travel_spd + 0.1)
                        print(f"  🚀 Viagem → {travel_spd:.1f}")
                    elif k == pygame.K_MINUS:
                        travel_spd = max(0.0, travel_spd - 0.1)
                        print(f"  🚀 Viagem → {travel_spd:.1f}")
                    elif k == pygame.K_SPACE:
                        audio_freeze = not audio_freeze
                        print(f"  ⏸  Áudio → {'FROZEN' if audio_freeze else 'LIVE'}")

            # ── Áudio ─────────────────────────────────────────────
            if audio_freeze:
                val, beat, bass, mid, high = frozen_data
            else:
                val, beat, bass, mid, high = audio.get_val()
                frozen_data = (val, beat, bass, mid, high)

            # ── Color offset automático ────────────────────────────
            # No beat: injeta velocidade proporcional à intensidade
            # Sem beat: desacelera suavemente (inércia)
            if beat > 0.5:
                color_offset_vel += beat * 0.08 + val * 0.04
            color_offset_vel *= 0.92          # atrito
            color_offset     += color_offset_vel

            t = (pygame.time.get_ticks() - start) / 1000.0

            # ── Uniforms ──────────────────────────────────────────
            prog['u_time'].value         = t
            prog['u_res'].value          = WIN_SIZE
            prog['u_audio'].value        = val
            prog['u_beat'].value         = beat
            prog['u_bass'].value         = bass
            prog['u_mid'].value          = mid
            prog['u_high'].value         = high
            prog['u_color_offset'].value = color_offset
            prog['u_palette'].value      = palette_idx
            prog['u_mode'].value         = mode_idx
            prog['u_vignette'].value     = vignette
            prog['u_travel'].value       = travel_spd
            prog['u_glow'].value         = glow_on
            prog['u_feedback'].value     = feedback_on

            tex_prev.use(0)
            prog['u_prev'].value = 0

            # ── Render principal ──────────────────────────────────
            fbo_main.use()
            ctx.clear()
            vao.render()

            # ── Glow gaussiano ping-pong ───────────────────────────
            if glow_on:
                glow_strength = 0.6 + val * 0.8 + beat * 0.5

                fbo_glowA.use(); ctx.clear()
                tex_main.use(0)
                gprog['u_tex'].value      = 0
                gprog['u_res'].value      = WIN_SIZE
                gprog['u_strength'].value = glow_strength
                gprog['u_dir'].value      = (1.0, 0.0)
                gvao.render()

                fbo_glowB.use(); ctx.clear()
                tex_glowA.use(0)
                gprog['u_tex'].value  = 0
                gprog['u_dir'].value  = (0.0, 1.0)
                gvao.render()

                ctx.screen.use(); ctx.clear()
                tex_main.use(0); tex_glowB.use(1)
                cprog['u_base'].value = 0
                cprog['u_glow'].value = 1
                cprog['u_mix'].value  = min(1.0, glow_strength * 0.5)
                cvao.render()
            else:
                ctx.screen.use(); ctx.clear()
                tex_main.use(0)
                gprog['u_tex'].value      = 0
                gprog['u_res'].value      = WIN_SIZE
                gprog['u_strength'].value = 0.0
                gprog['u_dir'].value      = (1.0, 0.0)
                gvao.render()

            # ── Salva prev para feedback ───────────────────────────
            fbo_prev.use(); ctx.clear()
            tex_main.use(0)
            gprog['u_tex'].value      = 0
            gprog['u_strength'].value = 0.0
            gprog['u_dir'].value      = (0.0, 0.0)
            gvao.render()

            pygame.display.flip()
            clock.tick(60)

    finally:
        audio.close()
        pygame.quit()


if __name__ == "__main__":
    main()
