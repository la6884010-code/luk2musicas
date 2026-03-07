#!/usr/bin/env python3
"""
Fractal Visualizer — Elite v3.3
+ Separação de reações por instrumento (kick / snare / hi-hat / sub-bass)
+ Túnel 3D Panda3D integrado (thread separada, áudio compartilhado)
+ Sistema de presets de fábrica (imutáveis) + presets do usuário (presets.json)
"""

import pygame
import moderngl
import numpy as np
import threading
import queue
import multiprocessing
import math
import random
import os
import subprocess
import time
import json
from collections import deque
from dataclasses import dataclass
from typing import Optional

# ── colorama (cores no terminal) ──────────────────────────────────
from colorama import init, Fore, Style
init(autoreset=True)

# ── opencv (opcional — gravação ao vivo) ──────────────────────────
try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

# ── Panda3D (opcional — túnel 3D) ─────────────────────────────────
try:
    from panda3d.core import (
        loadPrcFileData, Vec3, Point3, NodePath, LineSegs,
    )
    from direct.showbase.ShowBase import ShowBase
    from direct.task import Task
    PANDA3D_OK = True
except ImportError:
    PANDA3D_OK = False
    ShowBase = object

# --- Parâmetros ---
WIN_SIZE = (1280, 720)
CHUNK    = 1024

HELP = """
╔══════════════════════════════════════════════════════════════╗
║       FRACTAL VISUALIZER — ELITE  v3.3  + INSTRUMENTOS       ║
╠══════════════════════════════════════════════════════════════╣
║  P / ←→     Trocar paleta (5 paletas)                       ║
║  M          Trocar modo fractal (4 modos)                    ║
║  V / ↑↓     Ajustar vinheta                                 ║
║  G          Toggle glow (pós-processamento)                  ║
║  F          Toggle feedback de frame                         ║
║  Z          Toggle sincronização com BPM                     ║
║  C          Toggle câmera cinematográfica                    ║
║  T          Toggle túnel 3D (Panda3D)                        ║
║  [ / ]      Sensibilidade de beat ( - / + )                 ║
║  +/-        Velocidade de viagem no fractal                  ║
║  SPACE      Freeze / unfreeze áudio                          ║
║  R          Iniciar / parar gravação ao vivo                 ║
║  1-5        Ativar preset rápido                             ║
║  Q / E      Anterior / Próximo preset (todos)               ║
║  ESC        Sair                                             ║
╠══════════════════════════════════════════════════════════════╣
║  AUTOPILOT (troca automática por beat):                      ║
║  Y          Toggle autopilot ON/OFF                          ║
║  U          Aumentar ciclo  (2→4→8→16 beats)                ║
║  I          Diminuir ciclo  (16→8→4→2 beats)                ║
╠══════════════════════════════════════════════════════════════╣
║  PRESETS DE USUÁRIO:                                         ║
║  S          Salvar preset atual como preset do usuário       ║
║  X          Excluir preset do usuário ativo                  ║
║  BACKSPACE  Reset para presets LUK2                          ║
╠══════════════════════════════════════════════════════════════╣
║  HUD mostra: Modo · Paleta · BPM · Kick/Snare/HiHat/Sub     ║
╚══════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════
#  SISTEMA DE PRESETS
# ══════════════════════════════════════════════════════════════════

@dataclass
class Preset:
    name:             str
    mode:             int
    palette:          int
    glow:             bool
    feedback:         bool
    vignette:         float
    travel_speed:     float
    beat_sensitivity: float


# ── Presets de fábrica (imutáveis) ────────────────────────────────
PRESETS_DEFAULT: dict[str, Preset] = {
    "default": Preset(
        name="default",
        mode=0, palette=0, glow=True, feedback=False,
        vignette=1.5, travel_speed=0.3, beat_sensitivity=1.5,
    ),
    "neon_tunnel": Preset(
        name="neon_tunnel",
        mode=1, palette=1, glow=True, feedback=True,
        vignette=1.8, travel_speed=0.7, beat_sensitivity=1.3,
    ),
    "kaleid_dream": Preset(
        name="kaleid_dream",
        mode=2, palette=2, glow=True, feedback=False,
        vignette=1.4, travel_speed=0.2, beat_sensitivity=1.7,
    ),
    "plasma_rave": Preset(
        name="plasma_rave",
        mode=3, palette=3, glow=True, feedback=True,
        vignette=1.2, travel_speed=0.5, beat_sensitivity=1.2,
    ),
    "aurora_loop": Preset(
        name="aurora_loop",
        mode=0, palette=4, glow=False, feedback=True,
        vignette=2.0, travel_speed=0.4, beat_sensitivity=1.6,
    ),
}

# ── Caminho do JSON de presets do usuário ─────────────────────────
PRESETS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

# ── Presets do usuário e dicionário mesclado (populados em runtime) ──
USER_PRESETS:    dict[str, Preset] = {}
ALL_PRESETS:     dict[str, Preset] = {}
PRESET_KEYS:     list[str]         = []
ALL_PRESET_KEYS: list[str]         = []


# ── Funções utilitárias de preset ─────────────────────────────────

def preset_to_dict(p: Preset) -> dict:
    return {
        "name":              p.name,
        "mode":              p.mode,
        "palette":           p.palette,
        "glow":              p.glow,
        "feedback":          p.feedback,
        "vignette":          p.vignette,
        "travel":            p.travel_speed,
        "beat_sensitivity":  p.beat_sensitivity,
    }


def preset_from_dict(d: dict) -> Preset:
    return Preset(
        name=str(d["name"]),
        mode=int(d["mode"]),
        palette=int(d["palette"]),
        glow=bool(d["glow"]),
        feedback=bool(d["feedback"]),
        vignette=float(d["vignette"]),
        travel_speed=float(d["travel"]),
        beat_sensitivity=float(d["beat_sensitivity"]),
    )


def load_user_presets(path: str) -> dict[str, Preset]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result: dict[str, Preset] = {}
        for item in data:
            p = preset_from_dict(item)
            result[p.name] = p
        return result
    except Exception as e:
        print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  presets.json inválido ou corrompido: {e}. Ignorando presets do usuário.")
        return {}


def save_user_presets(path: str, user_presets: dict[str, Preset]) -> None:
    try:
        data = [preset_to_dict(p) for p in user_presets.values()]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Erro ao salvar presets.json: {e}")


def is_factory_preset(name: str) -> bool:
    return name in PRESETS_DEFAULT


def rebuild_all_presets() -> None:
    """Reconstrói ALL_PRESETS, PRESET_KEYS e ALL_PRESET_KEYS a partir dos presets LUK2 + usuário."""
    global ALL_PRESETS, PRESET_KEYS, ALL_PRESET_KEYS
    merged: dict[str, Preset] = dict(PRESETS_DEFAULT)
    for name, preset in USER_PRESETS.items():
        if name not in PRESETS_DEFAULT:
            merged[name] = preset
    ALL_PRESETS     = merged
    PRESET_KEYS     = list(ALL_PRESETS.keys())
    ALL_PRESET_KEYS = list(ALL_PRESETS.keys())


# ── Inicialização no carregamento do módulo ───────────────────────
USER_PRESETS = load_user_presets(PRESETS_JSON_PATH)
rebuild_all_presets()


def activate_preset(preset_name: str, state: dict, audio_analyzer=None) -> Preset:
    if preset_name not in ALL_PRESETS:
        raise KeyError(f"Preset '{preset_name}' não encontrado. "
                       f"Disponíveis: {list(ALL_PRESETS.keys())}")

    p = ALL_PRESETS[preset_name]
    state['mode_idx']    = p.mode
    state['palette_idx'] = p.palette
    state['glow_on']     = p.glow
    state['feedback_on'] = p.feedback
    state['vignette']    = p.vignette
    state['travel_spd']  = p.travel_speed

    if audio_analyzer is not None:
        audio_analyzer.beat_sensitivity = p.beat_sensitivity

    origem = "LUK2" if is_factory_preset(preset_name) else "usuário"
    print(Fore.CYAN + f"  🎛  Preset [{origem}] → {p.name}  "
          f"[modo={p.mode} paleta={p.palette} glow={p.glow} "
          f"feedback={p.feedback} vig={p.vignette:.1f} "
          f"travel={p.travel_speed:.1f} sens={p.beat_sensitivity:.1f}]")
    return p


# ══════════════════════════════════════════════════════════════════
#  SELEÇÃO DE ARQUIVO DE ÁUDIO
# ══════════════════════════════════════════════════════════════════
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a')

def pick_audio_file() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Busca recursiva em todas as subpastas
    found_paths = []
    for root, _, files in os.walk(script_dir):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS:
                found_paths.append(os.path.join(root, f))
    found_paths.sort()

    if not found_paths:
        print("\n╔══════════════════════════════════════════════════╗")
        print("║  ⚠  Nenhum arquivo de áudio encontrado na pasta  ║")
        print(f"║  Pasta: {script_dir[:44]:<44} ║")
        print("║  Formatos suportados: mp3 wav ogg flac aac m4a   ║")
        print("╚══════════════════════════════════════════════════╝\n")
        raise SystemExit(1)

    print("\n╔══════════════════════════════════════════════════╗")
    print("║          🎵  Arquivos de áudio encontrados        ║")
    print("╠══════════════════════════════════════════════════╣")
    for i, path in enumerate(found_paths, 1):
        name = os.path.relpath(path, script_dir)
        line = f"  [{i}]  {name}"
        print(f"║  {line:<48}║")
    print("╚══════════════════════════════════════════════════╝")

    while True:
        try:
            choice = input(f"\nEscolha (1-{len(found_paths)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(found_paths):
                chosen = found_paths[idx]
                print(f"\n  ▶  {os.path.relpath(chosen, script_dir)}\n")
                return chosen
            else:
                print(f"  Digite um número entre 1 e {len(found_paths)}.")
        except (ValueError, EOFError):
            print(f"  Digite um número entre 1 e {len(found_paths)}.")


# ══════════════════════════════════════════════════════════════════
#  OFFLINE AUDIO ANALYZER  — estendido com bandas por instrumento
# ══════════════════════════════════════════════════════════════════
class OfflineAudioAnalyzer:
    """
    Retorna 9 valores por chunk:
      (val, beat_flash,
       smooth_bass, smooth_mid, smooth_high,
       smooth_kick, smooth_snare, smooth_hihat, smooth_subbass)

    Bandas de instrumento:
      sub-bass  : 20–60 Hz
      kick      : 60–120 Hz
      snare     : 200–800 Hz   ← banda estreitada (era 200–2000 Hz)
      hi-hat    : 4000–20000 Hz
    """

    def __init__(self, sample_rate: int, beat_sensitivity: float = 1.5):
        self.beat_sensitivity = beat_sensitivity
        self._rate = sample_rate

        freqs = np.fft.rfftfreq(CHUNK, 1.0 / sample_rate)

        # ── Bandas gerais (usadas para glow / paleta / feedback) ──
        self.bass_idx = np.where((freqs >= 20)   & (freqs < 140))[0]
        self.mid_idx  = np.where((freqs >= 140)  & (freqs < 4000))[0]
        self.high_idx = np.where((freqs >= 4000) & (freqs < 20000))[0]

        # ── Bandas por instrumento ────────────────────────────────
        self.subbass_idx = np.where((freqs >= 20)   & (freqs <  60))[0]
        self.kick_idx    = np.where((freqs >= 60)   & (freqs < 120))[0]
        self.snare_idx   = np.where((freqs >= 200)  & (freqs < 800))[0]   # ← estreitado
        self.hihat_idx   = np.where((freqs >= 4000) & (freqs < 20000))[0]

        # ── Valores suavizados gerais ─────────────────────────────
        self.smooth_audio = 0.0
        self.smooth_bass  = 0.0
        self.smooth_mid   = 0.0
        self.smooth_high  = 0.0

        self.bass_max = 1e-6
        self.mid_max  = 1e-6
        self.high_max = 1e-6

        # ── Valores suavizados por instrumento ────────────────────
        self.smooth_kick    = 0.0
        self.smooth_snare   = 0.0
        self.smooth_hihat   = 0.0
        self.smooth_subbass = 0.0

        self.kick_max    = 1e-6
        self.snare_max   = 1e-6
        self.hihat_max   = 1e-6
        self.subbass_max = 1e-6

        # ── Detecção de beat ──────────────────────────────────────
        self.flux_history = deque(maxlen=43)
        self.beat_cool    = 0
        self.beat_flash   = 0.0

        self.prev_fft    = None
        self.flux_smooth = 0.0
        self.flux_peak   = 0.0

        self._cool_frames = max(8, int(0.30 * sample_rate / CHUNK))

    def process_chunk(self, data: np.ndarray):
        if len(data) < CHUNK:
            data = np.pad(data, (0, CHUNK - len(data)))
        else:
            data = data[:CHUNK]

        fft  = np.abs(np.fft.rfft(data * np.hanning(CHUNK)))
        peak = float(np.max(np.abs(data)))
        if peak < 0.025:
            peak = 0.0

        def band_rms(idx):
            if len(idx) == 0:
                return 0.0
            return float(np.sqrt(np.mean(fft[idx] ** 2)))

        # ── Bandas gerais ─────────────────────────────────────────
        bass = band_rms(self.bass_idx)
        mid  = band_rms(self.mid_idx)
        high = band_rms(self.high_idx)

        # ── Bandas por instrumento ────────────────────────────────
        kick_raw    = band_rms(self.kick_idx)
        snare_raw   = band_rms(self.snare_idx)
        hihat_raw   = band_rms(self.hihat_idx)
        subbass_raw = band_rms(self.subbass_idx)

        # ── Flux espectral (detecção de beat, base no kick) ───────
        if self.prev_fft is None:
            flux = 0.0
        else:
            diff = fft[self.bass_idx] - self.prev_fft[self.bass_idx]
            flux = float(np.sum(np.maximum(diff, 0.0)))
        self.prev_fft = fft.copy()

        self.flux_smooth = 0.3 * flux + 0.7 * self.flux_smooth
        flux = self.flux_smooth
        self.flux_peak = max(self.flux_peak * 0.98, flux)

        def smooth(old, new, up=0.35, dn=0.08):
            a = up if new > old else dn
            return old + (new - old) * a

        # ── Normalização bandas gerais ────────────────────────────
        self.bass_max = max(self.bass_max * 0.995, bass)
        self.mid_max  = max(self.mid_max  * 0.995, mid)
        self.high_max = max(self.high_max * 0.995, high)

        bass_n = min(bass / (self.bass_max + 1e-6), 1.0)
        mid_n  = min(mid  / (self.mid_max  + 1e-6), 1.0)
        high_n = min(high / (self.high_max + 1e-6), 1.0)

        # ── Normalização bandas por instrumento ───────────────────
        self.kick_max    = max(self.kick_max    * 0.995, kick_raw)
        self.snare_max   = max(self.snare_max   * 0.995, snare_raw)
        self.hihat_max   = max(self.hihat_max   * 0.995, hihat_raw)
        self.subbass_max = max(self.subbass_max * 0.995, subbass_raw)

        kick_n    = min(kick_raw    / (self.kick_max    + 1e-6), 1.0)
        snare_n   = min(snare_raw   / (self.snare_max   + 1e-6), 1.0)
        hihat_n   = min(hihat_raw   / (self.hihat_max   + 1e-6), 1.0)
        subbass_n = min(subbass_raw / (self.subbass_max + 1e-6), 1.0)

        # ── Suavização ────────────────────────────────────────────
        self.smooth_audio   = smooth(self.smooth_audio,   min(peak, 1.0))
        self.smooth_bass    = smooth(self.smooth_bass,    bass_n,    0.40, 0.06)
        self.smooth_mid     = smooth(self.smooth_mid,     mid_n,     0.30, 0.07)
        self.smooth_high    = smooth(self.smooth_high,    high_n,    0.50, 0.10)

        self.smooth_kick    = smooth(self.smooth_kick,    kick_n,    0.50, 0.07)
        self.smooth_snare   = smooth(self.smooth_snare,   snare_n,   0.40, 0.08)
        self.smooth_hihat   = smooth(self.smooth_hihat,   hihat_n,   0.60, 0.12)
        self.smooth_subbass = smooth(self.smooth_subbass, subbass_n, 0.35, 0.05)

        val = float(np.clip(self.smooth_audio, 0.0, 1.0))

        # ── Beat detection ────────────────────────────────────────
        self.flux_history.append(flux)
        detected_beat = False
        if len(self.flux_history) > 10:
            avg = float(np.mean(self.flux_history))
            var = float(np.var(self.flux_history))
            threshold = max(avg + var * self.beat_sensitivity, avg * 1.5)
            energy_ok = bass_n > 0.08
            is_peak   = flux >= self.flux_peak * 0.95
            if flux > threshold and energy_ok and is_peak and self.beat_cool <= 0:
                detected_beat = True
                self.beat_cool = self._cool_frames

        if self.beat_cool > 0:
            self.beat_cool -= 1

        if detected_beat:
            self.beat_flash = 1.0
        else:
            self.beat_flash *= 0.82

        return (
            val,
            float(self.beat_flash),
            float(self.smooth_bass),
            float(self.smooth_mid),
            float(self.smooth_high),
            float(self.smooth_kick),
            float(self.smooth_snare),
            float(self.smooth_hihat),
            float(self.smooth_subbass),
        )


# ══════════════════════════════════════════════════════════════════
#  FILE AUDIO ANALYZER
# ══════════════════════════════════════════════════════════════════
class FileAudioAnalyzer:
    def __init__(self, filepath: str):
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError(
                "Instale soundfile:  pip install soundfile\n"
                "Suporte a MP3:      pip install soundfile[mp3]  (ou pip install pydub)"
            )

        print(f"  📂 Carregando: {os.path.basename(filepath)}")
        audio_data, sample_rate = sf.read(filepath, dtype='float32', always_2d=False)
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        self._audio_data  = audio_data
        self._sample_rate = sample_rate
        self._filepath    = filepath

        dur = len(audio_data) / sample_rate
        print(f"  ✔  {dur:.1f}s  |  {sample_rate}Hz\n")

        self._ofa = OfflineAudioAnalyzer(sample_rate, beat_sensitivity=1.5)

        self.bpm      = 0.0
        self.bpm_sync = True
        self._beat_times = deque(maxlen=8)

        self._q       = queue.Queue(maxsize=8)
        self._running = True
        self._sens_lock = threading.Lock()  # protege beat_sensitivity entre threads

        pygame.mixer.init(frequency=sample_rate, size=-16, channels=1, buffer=2048)
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        self._start_time = pygame.time.get_ticks() / 1000.0

        self._thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self._thread.start()

    @property
    def beat_sensitivity(self):
        with self._sens_lock:
            return self._ofa.beat_sensitivity

    @beat_sensitivity.setter
    def beat_sensitivity(self, v):
        with self._sens_lock:
            self._ofa.beat_sensitivity = v

    def _analyze_loop(self):
        chunk_dur  = CHUNK / self._sample_rate
        sample_pos = 0
        total      = len(self._audio_data)

        while self._running and sample_pos < total:
            elapsed    = pygame.time.get_ticks() / 1000.0 - self._start_time
            target_pos = int(elapsed * self._sample_rate)
            sample_pos = max(sample_pos, target_pos)

            end = sample_pos + CHUNK
            if end > total:
                break

            chunk  = self._audio_data[sample_pos:end]
            result = self._ofa.process_chunk(chunk)  # 9-tuple

            val, beat_flash = result[0], result[1]
            if beat_flash > 0.9 and self.bpm_sync:
                now = pygame.time.get_ticks() / 1000.0
                self._beat_times.append(now)
                if len(self._beat_times) >= 2:
                    intervals = np.diff(list(self._beat_times))
                    _mean_iv = float(np.mean(intervals))
                    if _mean_iv > 0:
                        self.bpm = round(60.0 / _mean_iv)

            if self._q.full():
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
            self._q.put_nowait(result)

            sample_pos += CHUNK
            time.sleep(chunk_dur)  # dorme 1 chunk inteiro → análise ~0.88x real-time → max() sincroniza corretamente

    def get_val(self):
        """Retorna 9-tuple: (val, beat, bass, mid, high, kick, snare, hihat, subbass)"""
        try:
            return self._q.get_nowait()
        except queue.Empty:
            ofa = self._ofa
            return (
                float(ofa.smooth_audio),
                float(ofa.beat_flash),
                float(ofa.smooth_bass),
                float(ofa.smooth_mid),
                float(ofa.smooth_high),
                float(ofa.smooth_kick),
                float(ofa.smooth_snare),
                float(ofa.smooth_hihat),
                float(ofa.smooth_subbass),
            )

    def close(self):
        self._running = False
        pygame.mixer.music.stop()
        self._thread.join(timeout=1.0)


# ══════════════════════════════════════════════════════════════════
#  REAÇÕES VISUAIS POR INSTRUMENTO
# ══════════════════════════════════════════════════════════════════
class InstrumentReactions:
    """
    Converte intensidades de instrumento em estados visuais com decay.

    kick_zoom     → zoom pulsado no kick (bumbo)
    snare_flash   → flash branco na caixa  ← threshold e decay ajustados
    hihat_vib     → micro-vibração no hi-hat
    subbass_dist  → distorção lenta no sub-bass
    """

    def __init__(self):
        self.kick_zoom    = 0.0
        self.snare_flash  = 0.0
        self.hihat_vib    = 0.0
        self.subbass_dist = 0.0

    def update(self, kick: float, snare: float, hihat: float, subbass: float):
        # Kick → zoom pulsado  (resposta rápida, decay médio)
        if kick > 0.50:
            self.kick_zoom = min(1.0, self.kick_zoom + kick * 0.55)
        self.kick_zoom *= 0.78

        # Snare → flash branco  (threshold subido, decay mais rápido)
        if snare > 0.65:                                          # ← era 0.55
            self.snare_flash = min(1.0, self.snare_flash + snare * 0.60)
        self.snare_flash *= 0.55                                  # ← era 0.68

        # Hi-hat → vibração  (acumula rápido, vai embora rápido)
        if hihat > 0.40:
            self.hihat_vib = min(1.0, self.hihat_vib + hihat * 0.70)
        self.hihat_vib *= 0.60

        # Sub-bass → distorção lenta  (resposta lenta, decay muito lento)
        if subbass > 0.55:
            self.subbass_dist = min(1.0, self.subbass_dist + subbass * 0.25)
        self.subbass_dist *= 0.94

        return (
            float(self.kick_zoom),
            float(self.snare_flash),
            float(self.hihat_vib),
            float(self.subbass_dist),
        )


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
uniform float u_color_offset;
uniform int   u_palette;
uniform int   u_mode;
uniform float u_vignette;
uniform float u_travel;
uniform bool  u_glow;
uniform bool  u_feedback;
uniform sampler2D u_prev;

uniform bool  u_cinematic;
uniform float u_cam_zoom;
uniform vec2  u_cam_shake;
uniform vec2  u_cam_drift;
uniform float u_cam_parallax;

// ── Reações por instrumento ───────────────────────────────────────
uniform float u_kick_zoom;    // bump de zoom no bumbo
uniform float u_snare_flash;  // flash branco na caixa
uniform float u_hihat_vib;    // micro-vibração no hi-hat
uniform float u_subbass_dist; // distorção lenta no sub-bass

// ── Ocean Flow ────────────────────────────────────────────────────
uniform float u_calm;         // 0=música forte  1=música suave

vec3 aces(vec3 x) {
    return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0);
}

vec3 palette(float t, float co, float intensity) {
    t += co;
    vec3 a, b, c, d;

    if (u_palette == 0) {
        float fire = smoothstep(0.05, 0.6, intensity * 3.0) + u_beat * 0.4;
        a = mix(vec3(0.5,0.5,0.5), vec3(0.5,0.3,0.1), fire);
        b = mix(vec3(0.5,0.5,0.5), vec3(0.5,0.4,0.1), fire);
        c = mix(vec3(1.0,1.0,1.0), vec3(1.0,0.7,0.0), fire);
        d = mix(vec3(0.30,0.45,0.60), vec3(0.00,0.10,0.20), fire);
    }
    else if (u_palette == 1) {
        b = vec3(0.5 + u_bass * 0.3, 0.5, 0.0);
        a = vec3(0.5, 0.0, 0.5 + u_high * 0.3);
        c = vec3(1.0, 1.0, 1.0);
        d = vec3(0.00, 0.33, 0.67);
    }
    else if (u_palette == 2) {
        a = vec3(0.8, 0.7 + u_mid * 0.2, 0.9);
        b = vec3(0.2, 0.3, 0.2 + u_high * 0.3);
        c = vec3(1.0, 0.8, 0.9);
        d = vec3(0.10, 0.40, 0.20);
    }
    else if (u_palette == 3) {
        a = vec3(0.5, 0.5, 0.5);
        b = vec3(0.5 + u_bass * 0.3, 0.5, 0.5 + u_high * 0.3);
        c = vec3(2.0, 1.0 + u_mid, 0.0);
        d = vec3(0.50, 0.20, 0.25);
    }
    else {
        a = vec3(0.0, 0.5 + u_bass * 0.2, 0.4);
        b = vec3(0.1, 0.4, 0.3 + u_high * 0.2);
        c = vec3(0.5, 1.0, 0.8);
        d = vec3(0.00, 0.15, 0.50);
    }

    b *= 1.0 + intensity * 0.5;
    return a + b * cos(6.28318 * (c * t + d));
}

vec2 rot2(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(p.x*c - p.y*s, p.x*s + p.y*c);
}

#define PAL(t) palette(t, u_color_offset, u_audio)

vec2 applyCinematicCamera(vec2 uv, float layer) {
    if (!u_cinematic) return uv;
    float zoomScale = 1.0 / (1.0 + u_cam_zoom * layer);
    uv *= zoomScale;
    uv += u_cam_shake * layer;
    uv += u_cam_drift * layer;
    float parallaxAmount = u_cam_parallax * (1.0 - layer * 0.6);
    uv += uv * parallaxAmount;
    return uv;
}

// ── Distorção de sub-bass: warp lento tipo tremor ─────────────────
vec2 applySubbassDist(vec2 uv, float strength) {
    if (strength < 0.01) return uv;
    float wx = sin(u_time * 1.3 + uv.y * 2.8) * cos(u_time * 0.7 + uv.x * 1.5);
    float wy = cos(u_time * 1.1 + uv.x * 3.2) * sin(u_time * 0.9 + uv.y * 2.1);
    return uv + vec2(wx, wy) * strength * 0.045;
}

// ── Vibração de hi-hat: micro offset rápido ───────────────────────
vec2 applyHihatVib(vec2 uv, float strength) {
    if (strength < 0.01) return uv;
    float vx = sin(u_time * 90.0 + uv.y * 12.0) * 0.5
             + sin(u_time * 130.0 + uv.x * 8.0) * 0.5;
    float vy = cos(u_time * 85.0 + uv.x * 11.0) * 0.5
             + cos(u_time * 110.0 + uv.y * 9.0) * 0.5;
    return uv + vec2(vx, vy) * strength * 0.010;
}

vec3 modeLoop(vec2 uv0) {
    vec2 uv = uv0;
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

vec3 applyGlow(vec3 base) {
    if (!u_glow) return base;
    vec3 glow = base * 0.4 * (8.0 * 0.4);
    return base + glow / 8.0 * (0.4 + u_beat * 0.6);
}

void main() {
    vec2 uv0 = (gl_FragCoord.xy * 2.0 - u_res) / u_res.y;

    // ── Reação ao beat geral ──────────────────────────────────────
    uv0 += uv0 * u_beat  * 0.04 * sin(u_time * 8.0);
    uv0 += uv0 * u_high  * 0.015 * sin(u_time * 20.0 + uv0.x * 5.0);

    // ── Kick: zoom pulsado ────────────────────────────────────────
    uv0 *= 1.0 - u_kick_zoom * 0.10;

    // ── Hi-hat: micro-vibração ────────────────────────────────────
    uv0 = applyHihatVib(uv0, u_hihat_vib);

    // ── Sub-bass: distorção lenta de espaço ──────────────────────
    uv0 = applySubbassDist(uv0, u_subbass_dist);

    // ── Ocean Flow: ondulação suave em músicas calmas ─────────────
    if (u_calm > 0.001) {
        float spd = mix(0.25, 0.6, u_high);
        float amp = mix(0.001, 0.03, u_calm);
        float w1  = sin(uv0.y * 3.0 + u_time * spd);
        float w2  = cos(uv0.x * 2.2 + u_time * (spd * 0.7));
        uv0 += vec2(w1, w2) * amp;
    }

    vec2 uv_bg = applyCinematicCamera(uv0, 0.55);
    vec2 uv_fg = applyCinematicCamera(uv0, 1.0);

    vec2 uvMain  = uv_fg;
    vec2 uvDepth = uv_bg;

    vec3 col;
    if (u_mode == 0) {
        col = modeLoop(uvMain);
    }
    else if (u_mode == 1) {
        vec3 c_fg = modeTunnel(uvMain);
        vec3 c_bg = modeTunnel(uvDepth);
        col = mix(c_bg, c_fg, 0.7);
    }
    else if (u_mode == 2) {
        col = modeKaleid(uvMain);
    }
    else {
        col = modePlasma(uvMain);
    }

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
    col = mix(col, PAL(u_time * 0.1) * 1.5, u_beat * 0.14);

    float vig = smoothstep(u_vignette, u_vignette * 0.2, length(uv0));
    col *= vig;

    // ── Snare: flash tonal baseado na paleta ativa ───────────────
    vec3 tonal = PAL(u_time * 0.1 + 0.2);
    tonal = mix(tonal, vec3(1.0), 0.25);
    tonal *= 1.1;
    col = mix(col, tonal, u_snare_flash * 0.35);

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

# ── HUD overlay: RGBA passthrough com alpha blending ─────────────
HUD_FRAG = """
#version 330
in  vec2 v_uv;
out vec4 f_color;
uniform sampler2D u_tex;
void main() {
    f_color = texture(u_tex, v_uv);
}
"""


def make_quad(ctx, prog):
    verts = np.array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1], dtype='f4')
    vbo = ctx.buffer(verts)
    return ctx.vertex_array(prog, [(vbo, '2f', 'in_vert')])


# ══════════════════════════════════════════════════════════════════
#  CÂMERA CINEMATOGRÁFICA
# ══════════════════════════════════════════════════════════════════
class CinematicCamera:
    def __init__(self):
        self._zoom_vel      = 0.0
        self._zoom_acc      = 0.0
        self._zoom_decay    = 0.88
        self._shake_x       = 0.0
        self._shake_y       = 0.0
        self._shake_decay   = 0.78
        self._drift_phase_x = 0.0
        self._drift_phase_y = 1.57
        self._parallax_base = 0.018

    def update(self, t, beat, bass, val):
        dt = 1.0 / 60.0

        if beat > 0.5:
            impulse = beat * 0.018 + val * 0.004
            self._zoom_vel += impulse
        self._zoom_vel *= self._zoom_decay
        self._zoom_acc = self._zoom_acc * 0.92 + self._zoom_vel
        cam_zoom = float(np.clip(self._zoom_acc, 0.0, 0.06))

        if beat > 0.6 and bass > 0.15:
            seed_t = t * 7.3
            shake_amp = bass * 0.003 * beat
            self._shake_x = shake_amp * (np.sin(seed_t * 2.1) * 0.6 + np.sin(seed_t * 3.7) * 0.4)
            self._shake_y = shake_amp * (np.cos(seed_t * 1.9) * 0.6 + np.cos(seed_t * 4.1) * 0.4)
        else:
            self._shake_x *= self._shake_decay
            self._shake_y *= self._shake_decay

        cam_shake = (float(self._shake_x), float(self._shake_y))

        self._drift_phase_x += dt * 0.18
        self._drift_phase_y += dt * 0.13

        drift_amp = 0.004
        drift_x = drift_amp * np.sin(self._drift_phase_x) * np.cos(self._drift_phase_x * 0.31)
        drift_y = drift_amp * np.sin(self._drift_phase_y) * np.cos(self._drift_phase_y * 0.47)

        drift_mod = 1.0 + val * 0.4
        cam_drift = (float(drift_x * drift_mod), float(drift_y * drift_mod))

        cam_parallax = float(self._parallax_base * (1.0 + bass * 0.3))
        return cam_zoom, cam_shake, cam_drift, cam_parallax

    def reset(self):
        self._zoom_vel = 0.0
        self._zoom_acc = 0.0
        self._shake_x  = 0.0
        self._shake_y  = 0.0


# ══════════════════════════════════════════════════════════════════
#  HUD
# ══════════════════════════════════════════════════════════════════
def draw_hud(surface, mode_idx, palette_idx, bpm, val, bass, mid, high,
             glow_on, feedback_on, bpm_sync, sensitivity, cinematic_on,
             active_preset: Optional[str] = None,
             tunnel_on: bool = False,
             kick: float = 0.0, snare: float = 0.0,
             hihat: float = 0.0, subbass: float = 0.0,
             autopilot_on: bool = False, autopilot_every_beats: int = 4):
            # Marca d'água FREE
    watermark_font = pygame.font.SysFont("Arial", 18, bold=True)
    watermark = watermark_font.render("@luk2musicas", True, (255, 255, 255))
    watermark.set_alpha(80)
    surface.blit(watermark, (20, surface.get_height() - 30))
    
    font = pygame.font.SysFont("Consolas", 15)

    PALETTE_NAMES = ['Gelo/Fogo', 'Neon', 'Pastel', 'Psicodélica', 'Aurora']
    MODE_NAMES    = ['Loop Fractal', 'Tunnel', 'Caleidoscópio', 'Plasma']

    origem = ""
    if active_preset:
        origem = " [LUK2]" if is_factory_preset(active_preset) else " [usr]"

    lines = [
        f"Modo:    {MODE_NAMES[mode_idx]}",
        f"Paleta:  {PALETTE_NAMES[palette_idx]}",
        f"BPM:     {int(bpm) if bpm > 0 else '---'}",
        f"Beat:    {'ON' if bpm_sync else 'OFF'}  Sens: {sensitivity:.1f}x",
        f"Glow:    {'ON' if glow_on else 'OFF'}",
        f"Feedback:{'ON' if feedback_on else 'OFF'}",
        f"Camera:  {'ON' if cinematic_on else 'OFF'}",
        f"Tunel:   {'ON' if tunnel_on else 'OFF'}",
        f"Preset:  {(active_preset or '---') + origem}",
        f"Autopilot:{'ON' if autopilot_on else 'OFF'} | Every: {autopilot_every_beats} beats",
        "",
        f"▐{'█' * int(bass   * 12):12s}  Graves",
        f"▐{'█' * int(mid    * 12):12s}  Médios",
        f"▐{'█' * int(high   * 12):12s}  Agudos",
        "",
        f"▐{'█' * int(kick    * 12):12s}  Kick",
        f"▐{'█' * int(snare   * 12):12s}  Snare",
        f"▐{'█' * int(hihat   * 12):12s}  Hi-hat",
        f"▐{'█' * int(subbass * 12):12s}  Sub-bass",
    ]

    pad = 10
    for i, line in enumerate(lines):
        shadow = font.render(line, True, (0, 0, 0))
        text   = font.render(line, True, (200, 220, 255))
        surface.blit(shadow, (pad + 1, pad + 1 + i * 18))
        surface.blit(text,   (pad,     pad     + i * 18))


# ══════════════════════════════════════════════════════════════════
#  HELPER: aplica uniforms do shader  (inclui instrumentos)
# ══════════════════════════════════════════════════════════════════
def _set_uniforms(prog, t, resolution, val, beat, bass, mid, high,
                  state, color_offset,
                  cinematic_on=False,
                  cam_zoom=0.0, cam_shake=(0.0, 0.0),
                  cam_drift=(0.0, 0.0), cam_parallax=0.0,
                  kick_zoom=0.0, snare_flash=0.0,
                  hihat_vib=0.0, subbass_dist=0.0,
                  calm=0.0):

    prog['u_time'].value         = t
    prog['u_res'].value          = resolution
    prog['u_audio'].value        = val
    prog['u_beat'].value         = beat
    prog['u_bass'].value         = bass
    prog['u_mid'].value          = mid
    prog['u_high'].value         = high
    prog['u_color_offset'].value = color_offset
    prog['u_palette'].value      = state['palette_idx']
    prog['u_mode'].value         = state['mode_idx']
    prog['u_vignette'].value     = state['vignette']
    prog['u_travel'].value       = state['travel_spd']
    prog['u_glow'].value         = state['glow_on']
    prog['u_feedback'].value     = state['feedback_on']
    prog['u_cinematic'].value    = cinematic_on
    prog['u_cam_zoom'].value     = cam_zoom
    prog['u_cam_shake'].value    = cam_shake
    prog['u_cam_drift'].value    = cam_drift
    prog['u_cam_parallax'].value = cam_parallax
    prog['u_kick_zoom'].value    = kick_zoom
    prog['u_snare_flash'].value  = snare_flash
    prog['u_hihat_vib'].value    = hihat_vib
    prog['u_subbass_dist'].value = subbass_dist
    prog['u_calm'].value         = calm


# ══════════════════════════════════════════════════════════════════
#  TÚNEL 3D — Panda3D
# ══════════════════════════════════════════════════════════════════
if PANDA3D_OK:
    class TunnelWithCurves(ShowBase):
        _TUNNEL_LEN   = 300.0
        _TUNNEL_SEG   = 100
        _TUNNEL_RAD   = 5.0
        _RING_PTS     = 20
        _LONG_LINES   = 12

        def __init__(self, shared_arr):
            loadPrcFileData('', 'window-title Tunel 3D — Elite v3.3')
            loadPrcFileData('', 'win-size 800 600')
            loadPrcFileData('', 'win-origin 1285 0')
            loadPrcFileData('', 'background-color 0 0 0 1')

            super().__init__()
            self.disableMouse()

            self._sh        = shared_arr
            self._cam_y     = -20.0
            self._cam_speed = 8.0
            self._shake_x   = 0.0
            self._shake_y   = 0.0

            self._build_tunnel()
            self.taskMgr.add(self._update, "TunnelUpdate")

        def _build_tunnel(self):
            root = self.render.attach_new_node("TunnelRoot")
            segs = LineSegs()
            segs.set_thickness(1.5)

            N  = self._TUNNEL_SEG
            NP = self._RING_PTS
            L  = self._TUNNEL_LEN
            R  = self._TUNNEL_RAD

            def curve(y):
                return math.sin(y * 0.040) * 3.0, math.cos(y * 0.025) * 1.5

            def radius(y):
                return R + math.sin(y * 0.080) * 0.8

            def color(t, offset=0.0):
                h = (t + offset) % 1.0
                return (
                    abs(math.sin(h * math.pi))           * 0.6 + 0.2,
                    abs(math.sin((h + 0.33) * math.pi)) * 0.6 + 0.2,
                    abs(math.sin((h + 0.67) * math.pi)) * 0.8 + 0.2,
                )

            for ring in range(N + 1):
                t_ = ring / N
                y  = t_ * L
                cx, cz = curve(y)
                r_ = radius(y)
                cr, cg, cb = color(t_)
                segs.set_color(cr, cg, cb, 1.0)
                pts = [Point3(cx + math.cos(j * 2*math.pi/NP)*r_, y,
                              cz + math.sin(j * 2*math.pi/NP)*r_)
                       for j in range(NP + 1)]
                segs.move_to(pts[0])
                for p in pts[1:]:
                    segs.draw_to(p)

            for j in range(self._LONG_LINES):
                angle = j * 2 * math.pi / self._LONG_LINES
                first = True
                for ring in range(N + 1):
                    t_ = ring / N
                    y  = t_ * L
                    cx, cz = curve(y)
                    r_ = radius(y)
                    cr, cg, cb = color(t_, offset=0.5)
                    segs.set_color(cr, cg, cb, 0.65)
                    p = Point3(cx + math.cos(angle)*r_, y, cz + math.sin(angle)*r_)
                    if first:
                        segs.move_to(p); first = False
                    else:
                        segs.draw_to(p)

            root.attach_new_node(segs.create())

        def _update(self, task):
            if self._sh[5] < 0.5:
                self.userExit()
                return Task.done

            dt   = self.taskMgr.globalClock.getDt()
            beat = self._sh[1]
            bass = self._sh[2]

            target_spd      = 8.0 + bass * 20.0 + beat * 12.0
            self._cam_speed += (target_spd - self._cam_speed) * 0.12
            self._cam_y     += self._cam_speed * dt

            if self._cam_y >= self._TUNNEL_LEN - 5.0:
                self._cam_y = -20.0

            if beat > 0.5:
                amp = beat * 0.28 + bass * 0.10
                self._shake_x = (random.random() - 0.5) * amp
                self._shake_y = (random.random() - 0.5) * amp * 0.40
            else:
                self._shake_x *= 0.80
                self._shake_y *= 0.80

            y  = self._cam_y
            cx = math.sin(y * 0.040) * 3.0
            cz = math.cos(y * 0.025) * 1.5
            self.camera.set_pos(cx + self._shake_x, y, cz + 0.5 + self._shake_y)

            ly  = y + 10.0
            self.camera.look_at(Point3(math.sin(ly*0.040)*3.0, ly,
                                       math.cos(ly*0.025)*1.5 + 0.5))
            return Task.cont


def _launch_tunnel(shared_arr) -> None:
    if not PANDA3D_OK:
        return
    try:
        app = TunnelWithCurves(shared_arr)
        app.run()
    except Exception as e:
        print(Fore.YELLOW + Style.BRIGHT + f"⚠  Túnel 3D encerrou com erro: {e}")


# ══════════════════════════════════════════════════════════════════
#  RENDER OFFLINE
# ══════════════════════════════════════════════════════════════════
def render_offline(
    audio_path:  str,
    preset_name: str,
    output_path: str,
    resolution:  tuple = (1280, 720),
    fps:         int   = 30,
):
    try:
        import soundfile as sf
    except ImportError:
        raise ImportError("Instale soundfile:  pip install soundfile")
    try:
        import cv2
    except ImportError:
        raise ImportError("Instale opencv:  pip install opencv-python")

    if preset_name not in ALL_PRESETS:
        raise KeyError(f"Preset '{preset_name}' não existe. Disponíveis: {list(ALL_PRESETS.keys())}")

    audio_path  = os.path.abspath(audio_path)
    output_path = os.path.abspath(output_path)
    out_dir     = os.path.dirname(output_path)

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║           FRACTAL VISUALIZER — RENDER OFFLINE        ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Áudio  : {os.path.basename(audio_path):<42}║")
    print(f"║  Preset : {preset_name:<42}║")
    print(f"║  Saída  : {os.path.basename(output_path):<42}║")
    print(f"║  Pasta  : {out_dir[:42]:<42}║")
    print("╚══════════════════════════════════════════════════════╝\n")

    if not os.path.isfile(audio_path):
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO: arquivo de áudio não encontrado: {audio_path}")
        raise SystemExit(1)
    if not os.path.isdir(out_dir):
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO: pasta de destino não existe: {out_dir}")
        raise SystemExit(1)

    print(f"📂 Carregando áudio: {os.path.basename(audio_path)}")
    try:
        audio_data, sample_rate = sf.read(audio_path, dtype='float32', always_2d=False)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO ao ler o áudio: {e}")
        raise SystemExit(1)

    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    duracao = len(audio_data) / sample_rate
    print(f"   ✔  Duração: {duracao:.1f}s  |  Taxa: {sample_rate}Hz")

    state = {'mode_idx':0,'palette_idx':0,'glow_on':True,'feedback_on':False,
             'vignette':1.5,'travel_spd':0.3}
    preset = activate_preset(preset_name, state)

    analyzer          = OfflineAudioAnalyzer(sample_rate, beat_sensitivity=preset.beat_sensitivity)
    reactions         = InstrumentReactions()
    samples_per_frame = int(sample_rate / fps)
    total_frames      = len(audio_data) // samples_per_frame
    W, H              = resolution

    print(f"\n🖥  Criando contexto OpenGL offscreen…")
    try:
        ctx = moderngl.create_standalone_context()
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO ao criar contexto OpenGL: {e}")
        raise SystemExit(1)

    prog  = ctx.program(vertex_shader=VERTEX_SHADER,  fragment_shader=FRAGMENT_SHADER)
    gprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=GLOW_FRAG)
    cprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=COMPOSITE_FRAG)

    vao  = make_quad(ctx, prog)
    gvao = make_quad(ctx, gprog)
    cvao = make_quad(ctx, cprog)

    def make_fbo_off():
        tex = ctx.texture((W, H), 3, dtype='f4')
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        return ctx.framebuffer([tex]), tex

    fbo_main,  tex_main  = make_fbo_off()
    fbo_prev,  tex_prev  = make_fbo_off()
    fbo_glowA, tex_glowA = make_fbo_off()
    fbo_glowB, tex_glowB = make_fbo_off()
    fbo_out,   tex_out   = make_fbo_off()

    tmp_video = os.path.join(out_dir, "_tmp_fractal_render_.mp4")
    print(f"🎬 Iniciando gravação de vídeo…")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    try:
        writer = cv2.VideoWriter(tmp_video, fourcc, fps, (W, H))
        if not writer.isOpened():
            raise RuntimeError("VideoWriter não abriu.")
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO ao criar VideoWriter: {e}")
        raise SystemExit(1)

    print(f"   ✔  VideoWriter pronto")
    print(f"\n🎬 Renderizando {total_frames} frames @ {fps}fps  |  {W}×{H}  |  Preset: {preset_name}\n")

    color_offset = color_offset_vel = 0.0
    render_start = time.time()

    for frame_idx in range(total_frames):
        s0    = frame_idx * samples_per_frame
        chunk = audio_data[s0: s0 + samples_per_frame]

        val, beat, bass, mid, high, kick, snare, hihat, subbass = analyzer.process_chunk(chunk)
        kick_zoom, snare_flash, hihat_vib, subbass_dist = reactions.update(kick, snare, hihat, subbass)

        t = frame_idx / fps

        if beat > 0.5:
            color_offset_vel += beat * 0.08 + val * 0.04
        color_offset_vel *= 0.92
        color_offset     += color_offset_vel

        tex_prev.use(0); prog['u_prev'].value = 0
        _set_uniforms(prog, t, (W, H), val, beat, bass, mid, high, state, color_offset,
                      kick_zoom=kick_zoom, snare_flash=snare_flash,
                      hihat_vib=hihat_vib, subbass_dist=subbass_dist)

        fbo_main.use(); ctx.clear(); vao.render()

        if state['glow_on']:
            gs = 0.6 + val * 0.8 + beat * 0.5
            fbo_glowA.use(); ctx.clear()
            tex_main.use(0)
            gprog['u_tex'].value=0; gprog['u_res'].value=(W,H)
            gprog['u_strength'].value=gs; gprog['u_dir'].value=(1.0,0.0); gvao.render()
            fbo_glowB.use(); ctx.clear()
            tex_glowA.use(0); gprog['u_tex'].value=0; gprog['u_dir'].value=(0.0,1.0); gvao.render()
            fbo_out.use(); ctx.clear()
            tex_main.use(0); tex_glowB.use(1)
            cprog['u_base'].value=0; cprog['u_glow'].value=1
            cprog['u_mix'].value=min(1.0,gs*0.5); cvao.render()
            read_fbo = fbo_out
        else:
            read_fbo = fbo_main

        fbo_prev.use(); ctx.clear()
        tex_main.use(0); gprog['u_tex'].value=0
        gprog['u_strength'].value=0.0; gprog['u_dir'].value=(0.0,0.0); gvao.render()

        raw   = np.frombuffer(read_fbo.read(components=3, dtype='f4'), dtype=np.float32)
        frame = (raw.reshape(H, W, 3) * 255.0).clip(0,255).astype(np.uint8)
        frame_bgr = cv2.cvtColor(np.flipud(frame), cv2.COLOR_RGB2BGR)
        writer.write(frame_bgr)

        if frame_idx % max(1, fps // 4) == 0 or frame_idx == total_frames - 1:
            elapsed  = time.time() - render_start
            pct      = (frame_idx + 1) / total_frames
            eta_s    = (elapsed / pct) * (1.0 - pct) if pct > 0 else 0
            bar_done = int(pct * 30)
            bar      = '█' * bar_done + '░' * (30 - bar_done)
            tempo_s  = int(t)
            minutos  = tempo_s // 60
            segundos = tempo_s % 60
            eta_m    = int(eta_s) // 60
            eta_ss   = int(eta_s) % 60
            print(
                f"\r  [{bar}] {pct*100:5.1f}%  "
                f"frame {frame_idx+1}/{total_frames}  "
                f"pos {minutos:02d}:{segundos:02d}  "
                f"ETA {eta_m:02d}:{eta_ss:02d}",
                end='', flush=True
            )

    writer.release()
    elapsed_total = time.time() - render_start
    print(f"\n\n✅ Frames prontos em {elapsed_total:.1f}s  →  {tmp_video}")

    print(f"\n🔊 Adicionando áudio com ffmpeg…")
    ffmpeg_ok = False
    try:
        subprocess.run(
            ['ffmpeg', '-y',
             '-i', tmp_video,
             '-i', audio_path,
             '-c:v', 'copy',
             '-c:a', 'aac',
             '-b:a', '192k',
             '-shortest',
             output_path],
            check=True, capture_output=True, text=True
        )
        ffmpeg_ok = True
        print("   ✔  ffmpeg executou com sucesso")
    except FileNotFoundError:
        print(Fore.RED + Style.BRIGHT + "❌ ERRO: ffmpeg não encontrado no PATH.")
    except subprocess.CalledProcessError as e:
        print(Fore.RED + Style.BRIGHT + f"❌ ERRO no ffmpeg (código {e.returncode}):")
        for linha in (e.stderr or "").strip().splitlines()[-8:]:
            print(f"   {linha}")

    if ffmpeg_ok:
        try:
            os.remove(tmp_video)
        except Exception:
            pass
        print(Fore.GREEN + Style.BRIGHT + f"\n🎉 Vídeo salvo com sucesso!\n   📁 {output_path}\n")
    else:
        fallback = output_path.replace('.mp4', '_sem_audio.mp4')
        try:
            os.rename(tmp_video, fallback)
            print(Fore.YELLOW + Style.BRIGHT + f"\n⚠  Salvo SEM áudio em:\n   📁 {fallback}\n")
        except Exception as e:
            print(Fore.RED + Style.BRIGHT + f"\n❌ Não foi possível mover o temporário: {e}\n   {tmp_video}\n")


# ══════════════════════════════════════════════════════════════════
#  MAIN — loop realtime
# ══════════════════════════════════════════════════════════════════
def main():
    print(HELP)

    audio_path = pick_audio_file()

    shared_panda = multiprocessing.Array('d', [0.0, 0.0, 0.0, 0.0, 0.0, 1.0])

    tunnel_on      = False
    tunnel_process: Optional[multiprocessing.Process] = None

    def _start_tunnel():
        nonlocal tunnel_process
        if tunnel_process and tunnel_process.is_alive():
            return
        shared_panda[5] = 1.0
        tunnel_process = multiprocessing.Process(
            target=_launch_tunnel, args=(shared_panda,),
            daemon=True, name="Panda3D-Tunnel")
        tunnel_process.start()
        print("  🚇 Túnel 3D iniciado (janela separada)")

    def _stop_tunnel():
        shared_panda[5] = 0.0
        print("  🚇 Túnel 3D encerrando…")

    pygame.init()
    pygame.display.set_caption("◈ Fractal Visualizer — Elite v3.3")
    screen = pygame.display.set_mode(WIN_SIZE, pygame.OPENGL | pygame.DOUBLEBUF)
    ctx    = moderngl.create_context()

    audio     = FileAudioAnalyzer(audio_path)
    camera    = CinematicCamera()
    reactions = InstrumentReactions()

    prog  = ctx.program(vertex_shader=VERTEX_SHADER,  fragment_shader=FRAGMENT_SHADER)
    gprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=GLOW_FRAG)
    cprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=COMPOSITE_FRAG)
    hprog = ctx.program(vertex_shader=GLOW_VERT,      fragment_shader=HUD_FRAG)

    vao  = make_quad(ctx, prog)
    gvao = make_quad(ctx, gprog)
    cvao = make_quad(ctx, cprog)
    hvao = make_quad(ctx, hprog)

    W, H = WIN_SIZE

    def make_fbo():
        tex = ctx.texture((W, H), 3, dtype='f4')
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        return ctx.framebuffer([tex]), tex

    # Textura RGBA para o HUD overlay (uint8, criada uma vez)
    hud_tex = ctx.texture((W, H), 4)
    hud_tex.filter  = (moderngl.LINEAR, moderngl.LINEAR)
    hud_tex.swizzle = 'RGBA'

    fbo_main,  tex_main  = make_fbo()
    fbo_prev,  tex_prev  = make_fbo()
    fbo_glowA, tex_glowA = make_fbo()
    fbo_glowB, tex_glowB = make_fbo()
    fbo_out,   tex_out   = make_fbo()

    state = {
        'mode_idx':    0,
        'palette_idx': 0,
        'glow_on':     True,
        'feedback_on': False,
        'vignette':    1.5,
        'travel_spd':  0.3,
    }
    active_preset         = None
    current_preset_index  = 0
    block_mode_palette_until = 0
    vignette         = state['vignette']
    glow_on          = state['glow_on']
    feedback_on      = state['feedback_on']
    travel_spd       = state['travel_spd']
    audio_freeze     = False
    frozen_data      = (0.0,) * 9
    cinematic_on     = False
    color_offset     = 0.0
    color_offset_vel = 0.0

    # ── Autopilot por beat ────────────────────────────────────────
    autopilot_on              = False
    autopilot_every_beats     = 4
    autopilot_beat_counter    = 0
    autopilot_last_trigger_ms = 0
    autopilot_cooldown_ms     = 400   # ms mínimos entre triggers
    autopilot_last_beat_state = False  # para detecção de borda (edge)

    # ── Ocean Flow ────────────────────────────────────────────────
    calm_level = 0.0

    live_rec          = False
    live_writer       = None
    live_tmp_path     = ""
    live_out_path     = ""
    live_start_ms     = 0
    live_frame_count  = 0

    PALETTE_NAMES = ['Gelo/Fogo', 'Neon', 'Pastel', 'Psicodélica', 'Aurora']
    MODE_NAMES    = ['Loop Fractal', 'Tunnel', 'Caleidoscópio', 'Plasma']

    # ── Constrói mapa de teclas 1–5 a partir dos PRESET_KEYS atuais ──
    def make_preset_key_map() -> dict:
        _NUMKEYS = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]
        return {_NUMKEYS[i]: PRESET_KEYS[i] for i in range(min(5, len(PRESET_KEYS)))}

    PRESET_KEY_MAP = make_preset_key_map()

    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    k = event.key

                    # ── Presets numéricos 1–5 ─────────────────────
                    if k in PRESET_KEY_MAP:
                        active_preset = PRESET_KEY_MAP[k]
                        activate_preset(active_preset, state, audio)
                        glow_on     = state['glow_on']
                        feedback_on = state['feedback_on']
                        travel_spd  = state['travel_spd']
                        vignette    = state['vignette']
                        autopilot_beat_counter = 0  # evita troca imediata

                    elif k == pygame.K_ESCAPE:
                        return

                    # ── S: salvar preset do usuário ───────────────
                    elif k == pygame.K_s:
                        preset_name_input = input("  💾 Nome do novo preset: ").strip()
                        if not preset_name_input:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  Nome vazio. Operação cancelada.")
                        elif is_factory_preset(preset_name_input):
                            print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  '{preset_name_input}' é um preset LUK2 e não pode ser sobrescrito. Escolha outro nome.")
                        else:
                            novo = Preset(
                                name=preset_name_input,
                                mode=state['mode_idx'],
                                palette=state['palette_idx'],
                                glow=state['glow_on'],
                                feedback=state['feedback_on'],
                                vignette=state['vignette'],
                                travel_speed=state['travel_spd'],
                                beat_sensitivity=audio.beat_sensitivity,
                            )
                            USER_PRESETS[preset_name_input] = novo
                            save_user_presets(PRESETS_JSON_PATH, USER_PRESETS)
                            rebuild_all_presets()
                            PRESET_KEY_MAP = make_preset_key_map()
                            active_preset = preset_name_input
                            current_preset_index = ALL_PRESET_KEYS.index(preset_name_input) if preset_name_input in ALL_PRESET_KEYS else 0
                            print(Fore.CYAN + f"  💾 Preset do usuário '{preset_name_input}' salvo!")

                    # ── X: excluir preset do usuário ativo ────────
                    elif k == pygame.K_x:
                        if active_preset is None:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  Nenhum preset ativo selecionado.")
                        elif is_factory_preset(active_preset):
                            print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Preset LUK2 não pode ser apagado.")
                        elif active_preset not in USER_PRESETS:
                            print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  '{active_preset}' não está nos presets do usuário.")
                        else:
                            del USER_PRESETS[active_preset]
                            save_user_presets(PRESETS_JSON_PATH, USER_PRESETS)
                            rebuild_all_presets()
                            PRESET_KEY_MAP = make_preset_key_map()
                            current_preset_index = 0
                            print(Fore.CYAN + f"  🗑  Preset '{active_preset}' apagado.")
                            active_preset = None

                    # ── BACKSPACE: reset para LUK2 ────────────────
                    elif k == pygame.K_BACKSPACE:
                        backup_path = PRESETS_JSON_PATH.replace('.json', '.backup.json')
                        try:
                            if os.path.isfile(PRESETS_JSON_PATH):
                                os.rename(PRESETS_JSON_PATH, backup_path)
                                print(f"  🔄 presets.json renomeado para presets.backup.json")
                        except Exception as e:
                            print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Erro ao renomear presets.json: {e}")
                        USER_PRESETS.clear()
                        rebuild_all_presets()
                        PRESET_KEY_MAP = make_preset_key_map()
                        current_preset_index = 0
                        active_preset = None
                        print("  🔄 Reset para presets LUK2 concluído.")

                    elif k == pygame.K_t:
                        if not PANDA3D_OK:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  Panda3D não instalado — pip install panda3d")
                        else:
                            tunnel_on = not tunnel_on
                            (_start_tunnel if tunnel_on else _stop_tunnel)()
                    elif k in (pygame.K_p, pygame.K_RIGHT):
                        if pygame.time.get_ticks() >= block_mode_palette_until:
                            state['palette_idx'] = (state['palette_idx'] + 1) % 5
                            active_preset = None
                            print(Fore.YELLOW + f"  🎨 Paleta → {PALETTE_NAMES[state['palette_idx']]}")
                    elif k == pygame.K_LEFT:
                        if pygame.time.get_ticks() >= block_mode_palette_until:
                            state['palette_idx'] = (state['palette_idx'] - 1) % 5
                            active_preset = None
                            print(Fore.YELLOW + f"  🎨 Paleta → {PALETTE_NAMES[state['palette_idx']]}")
                    elif k == pygame.K_m:
                        if pygame.time.get_ticks() >= block_mode_palette_until:
                            state['mode_idx'] = (state['mode_idx'] + 1) % 4
                            active_preset = None
                            print(Fore.MAGENTA + f"  🔷 Modo → {MODE_NAMES[state['mode_idx']]}")
                    elif k in (pygame.K_v, pygame.K_UP):
                        vignette = min(2.5, vignette + 0.1)
                        state['vignette'] = vignette
                        print(Fore.BLUE + f"  🔆 Vinheta → {vignette:.1f}")
                    elif k == pygame.K_DOWN:
                        vignette = max(0.4, vignette - 0.1)
                        state['vignette'] = vignette
                        print(Fore.BLUE + f"  🔆 Vinheta → {vignette:.1f}")
                    elif k == pygame.K_g:
                        glow_on = not glow_on
                        state['glow_on'] = glow_on
                        print(Fore.LIGHTYELLOW_EX + f"  ✨ Glow → {'ON' if glow_on else 'OFF'}")
                    elif k == pygame.K_f:
                        feedback_on = not feedback_on
                        state['feedback_on'] = feedback_on
                        print(Fore.LIGHTGREEN_EX + f"  🔁 Feedback → {'ON' if feedback_on else 'OFF'}")
                    elif k == pygame.K_z:
                        audio.bpm_sync = not audio.bpm_sync
                        print(Fore.LIGHTRED_EX + f"  🥁 BPM Sync → {'ON' if audio.bpm_sync else 'OFF'}")

                    # ── Y → toggle autopilot ──────────────────────
                    elif k == pygame.K_y:
                        autopilot_on = not autopilot_on
                        autopilot_beat_counter = 0
                        print(Fore.CYAN + Style.BRIGHT +
                              f"  🤖 Autopilot → {'ON' if autopilot_on else 'OFF'}"
                              f"  (every {autopilot_every_beats} beats)")

                    # ── U → aumentar ciclo de beats ───────────────
                    elif k == pygame.K_u:
                        _AP_STEPS = [2, 4, 8, 16]
                        _ap_idx = _AP_STEPS.index(autopilot_every_beats) if autopilot_every_beats in _AP_STEPS else 1
                        autopilot_every_beats = _AP_STEPS[(_ap_idx + 1) % len(_AP_STEPS)]
                        print(Fore.CYAN + f"  🤖 Autopilot ciclo → {autopilot_every_beats} beats")

                    # ── I → diminuir ciclo de beats ───────────────
                    elif k == pygame.K_i:
                        _AP_STEPS = [2, 4, 8, 16]
                        _ap_idx = _AP_STEPS.index(autopilot_every_beats) if autopilot_every_beats in _AP_STEPS else 1
                        autopilot_every_beats = _AP_STEPS[(_ap_idx - 1) % len(_AP_STEPS)]
                        print(Fore.CYAN + f"  🤖 Autopilot ciclo → {autopilot_every_beats} beats")

                    # ── Q → preset anterior ───────────────────────
                    elif k == pygame.K_q:
                        if not ALL_PRESET_KEYS:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  Nenhum preset disponível para navegar.")
                        else:
                            current_preset_index = (current_preset_index - 1) % len(ALL_PRESET_KEYS)
                            active_preset = ALL_PRESET_KEYS[current_preset_index]
                            activate_preset(active_preset, state, audio)
                            glow_on     = state['glow_on']
                            feedback_on = state['feedback_on']
                            travel_spd  = state['travel_spd']
                            vignette    = state['vignette']
                            autopilot_beat_counter = 0  # evita troca imediata

                    # ── E → próximo preset ────────────────────────
                    elif k == pygame.K_e:
                        if not ALL_PRESET_KEYS:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  Nenhum preset disponível para navegar.")
                        else:
                            current_preset_index = (current_preset_index + 1) % len(ALL_PRESET_KEYS)
                            active_preset = ALL_PRESET_KEYS[current_preset_index]
                            activate_preset(active_preset, state, audio)
                            glow_on     = state['glow_on']
                            feedback_on = state['feedback_on']
                            travel_spd  = state['travel_spd']
                            vignette    = state['vignette']
                            autopilot_beat_counter = 0  # evita troca imediata

                    elif k == pygame.K_c:
                        cinematic_on = not cinematic_on
                        if not cinematic_on:
                            camera.reset()
                        print(f"  🎥 Câmera → {'ON' if cinematic_on else 'OFF'}")
                    elif k == pygame.K_RIGHTBRACKET:
                        audio.beat_sensitivity = min(3.0, audio.beat_sensitivity + 0.1)
                        print(f"  🎚 Sensibilidade → {audio.beat_sensitivity:.1f}x")
                    elif k == pygame.K_LEFTBRACKET:
                        audio.beat_sensitivity = max(1.1, audio.beat_sensitivity - 0.1)
                        print(f"  🎚 Sensibilidade → {audio.beat_sensitivity:.1f}x")
                    elif k in (pygame.K_PLUS, pygame.K_EQUALS):
                        travel_spd = min(2.0, travel_spd + 0.1)
                        state['travel_spd'] = travel_spd
                        print(Fore.GREEN + f"  🚀 Viagem → {travel_spd:.1f}")
                    elif k == pygame.K_MINUS:
                        travel_spd = max(0.0, travel_spd - 0.1)
                        state['travel_spd'] = travel_spd
                        print(Fore.GREEN + f"  🚀 Viagem → {travel_spd:.1f}")
                    elif k == pygame.K_SPACE:
                        audio_freeze = not audio_freeze
                        if audio_freeze:
                            pygame.mixer.music.pause()
                        else:
                            pygame.mixer.music.unpause()
                        print(Fore.WHITE + f"  ⏸  Áudio → {'FROZEN' if audio_freeze else 'LIVE'}")

                    elif k == pygame.K_r:
                        if not CV2_OK:
                            print(Fore.YELLOW + Style.BRIGHT + "  ⚠  opencv não encontrado — pip install opencv-python")
                        elif not live_rec:
                            script_dir    = os.path.dirname(os.path.abspath(audio_path))
                            ts            = time.strftime("%Y%m%d_%H%M%S")
                            live_out_path = os.path.join(script_dir, f"gravacao_{ts}.mp4")
                            live_tmp_path = os.path.join(script_dir, f"_tmp_live_{ts}.mp4")
                            fourcc        = cv2.VideoWriter_fourcc(*'mp4v')
                            live_writer   = cv2.VideoWriter(live_tmp_path, fourcc, 30, WIN_SIZE)
                            if live_writer.isOpened():
                                live_rec         = True
                                live_start_ms    = pygame.mixer.music.get_pos()
                                live_frame_count = 0
                                print(Fore.RED + Style.BRIGHT + f"  🔴 GRAVANDO → {os.path.basename(live_out_path)}")
                                print(f"     Aperte R novamente para parar.")
                            else:
                                live_writer = None
                                print(Fore.RED + Style.BRIGHT + f"  ❌ ERRO: não foi possível iniciar gravação.")
                        else:
                            live_rec      = False
                            live_end_ms   = pygame.mixer.music.get_pos()
                            duration_s    = max(0.1, (live_end_ms - live_start_ms) / 1000.0)
                            start_s       = live_start_ms / 1000.0
                            live_writer.release()
                            live_writer   = None
                            print(f"  ⏹  Gravação parada — {duration_s:.1f}s gravados")
                            print(f"  🔊 Adicionando áudio com ffmpeg…")
                            try:
                                subprocess.run(
                                    ['ffmpeg', '-y',
                                     '-i', live_tmp_path,
                                     '-ss', f"{start_s:.3f}",
                                     '-t',  f"{duration_s:.3f}",
                                     '-i',  audio_path,
                                     '-c:v', 'copy',
                                     '-c:a', 'aac', '-b:a', '192k',
                                     '-shortest',
                                     live_out_path],
                                    check=True, capture_output=True, text=True
                                )
                                os.remove(live_tmp_path)
                                print(Fore.GREEN + Style.BRIGHT + f"  🎉 Salvo com áudio: {live_out_path}")
                            except FileNotFoundError:
                                print(Fore.RED + Style.BRIGHT + "  ❌ ERRO: ffmpeg não encontrado no PATH.")
                                os.rename(live_tmp_path, live_out_path)
                                print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Salvo SEM áudio: {live_out_path}")
                            except subprocess.CalledProcessError as e:
                                linhas = (e.stderr or "").strip().splitlines()
                                print(Fore.RED + Style.BRIGHT + f"  ❌ ERRO ffmpeg (código {e.returncode}):")
                                for ln in linhas[-6:]:
                                    print(f"     {ln}")
                                try:
                                    os.rename(live_tmp_path, live_out_path)
                                except Exception:
                                    pass
                                print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Salvo SEM áudio: {live_out_path}")

            # ── Lê áudio (9-tuple) ────────────────────────────────────
            if audio_freeze:
                val, beat, bass, mid, high, kick, snare, hihat, subbass = frozen_data
            else:
                val, beat, bass, mid, high, kick, snare, hihat, subbass = audio.get_val()
                frozen_data = (val, beat, bass, mid, high, kick, snare, hihat, subbass)

            # ── Atualiza estados visuais por instrumento ──────────────
            kick_zoom, snare_flash, hihat_vib, subbass_dist = reactions.update(
                kick, snare, hihat, subbass
            )

            # ── Ocean Flow: detector de suavidade ─────────────────────
            energy = 0.55 * bass + 0.45 * mid
            target_calm = 1.0 if energy < 0.18 else 0.0
            # sobe devagar, desce rápido
            if target_calm > calm_level:
                calm_level = calm_level * 0.985 + target_calm * 0.015
            else:
                calm_level = calm_level * 0.93 + target_calm * 0.07
            calm_level = max(0.0, min(1.0, calm_level))

            # ── Autopilot por beat ────────────────────────────────────
            # Detecção de borda de subida: beat_flash cruzou 0.9 para cima
            _beat_now   = (beat > 0.9)
            _beat_edge  = _beat_now and (not autopilot_last_beat_state)
            autopilot_last_beat_state = _beat_now

            if autopilot_on and _beat_edge and ALL_PRESET_KEYS:
                autopilot_beat_counter += 1
                if autopilot_beat_counter % autopilot_every_beats == 0:
                    _now_ms = pygame.time.get_ticks()
                    if (_now_ms - autopilot_last_trigger_ms) >= autopilot_cooldown_ms:
                        current_preset_index = (current_preset_index + 1) % len(ALL_PRESET_KEYS)
                        active_preset        = ALL_PRESET_KEYS[current_preset_index]
                        activate_preset(active_preset, state, audio)
                        glow_on     = state['glow_on']
                        feedback_on = state['feedback_on']
                        travel_spd  = state['travel_spd']
                        vignette    = state['vignette']
                        autopilot_last_trigger_ms = _now_ms
                        print(Fore.CYAN + Style.BRIGHT +
                              f"  🤖 Autopilot → preset {active_preset}"
                              f" (every {autopilot_every_beats} beats)")

            shared_panda[0] = val   # sempre atualizado — tunnel usa sh[0] até sh[5]=0
            shared_panda[1] = beat
            shared_panda[2] = bass
            shared_panda[3] = mid
            shared_panda[4] = high

            if beat > 0.5:
                color_offset_vel += beat * 0.08 + val * 0.04
            color_offset_vel *= 0.92
            color_offset     += color_offset_vel

            t = (pygame.time.get_ticks() - start) / 1000.0

            if cinematic_on:
                cam_zoom, cam_shake, cam_drift, cam_parallax = camera.update(t, beat, bass, val)
            else:
                cam_zoom = 1.0 + beat * 0.1
                cam_shake = (0.2, 0.2); cam_drift = (0.5, 0.02); cam_parallax = 0.05

            tex_prev.use(0); prog['u_prev'].value = 0
            _set_uniforms(prog, t, WIN_SIZE, val, beat, bass, mid, high,
                          state, color_offset,
                          cinematic_on, cam_zoom, cam_shake, cam_drift, cam_parallax,
                          kick_zoom=kick_zoom, snare_flash=snare_flash,
                          hihat_vib=hihat_vib, subbass_dist=subbass_dist,
                          calm=calm_level)

            fbo_main.use(); ctx.clear(); vao.render()

            if glow_on:
                gs = 0.6 + val * 0.8 + beat * 0.5
                fbo_glowA.use(); ctx.clear()
                tex_main.use(0)
                gprog['u_tex'].value=0; gprog['u_res'].value=WIN_SIZE
                gprog['u_strength'].value=gs; gprog['u_dir'].value=(1.0,0.0); gvao.render()
                fbo_glowB.use(); ctx.clear()
                tex_glowA.use(0); gprog['u_tex'].value=0; gprog['u_dir'].value=(0.0,1.0); gvao.render()
                fbo_out.use(); ctx.clear()
                tex_main.use(0); tex_glowB.use(1)
                cprog['u_base'].value=0; cprog['u_glow'].value=1
                cprog['u_mix'].value=min(1.0,gs*0.5); cvao.render()
                ctx.screen.use(); ctx.clear()
                tex_out.use(0)
                gprog['u_tex'].value=0; gprog['u_res'].value=WIN_SIZE
                gprog['u_strength'].value=0.0; gprog['u_dir'].value=(0.0,0.0); gvao.render()
            else:
                fbo_out.use(); ctx.clear()
                tex_main.use(0)
                gprog['u_tex'].value=0; gprog['u_res'].value=WIN_SIZE
                gprog['u_strength'].value=0.0; gprog['u_dir'].value=(0.0,0.0); gvao.render()
                ctx.screen.use(); ctx.clear()
                tex_out.use(0)
                gprog['u_tex'].value=0; gprog['u_res'].value=WIN_SIZE
                gprog['u_strength'].value=0.0; gprog['u_dir'].value=(0.0,0.0); gvao.render()

            fbo_prev.use(); ctx.clear()
            tex_main.use(0); gprog['u_tex'].value=0
            gprog['u_strength'].value=0.0; gprog['u_dir'].value=(0.0,0.0); gvao.render()

            if live_rec and live_writer is not None:
                live_frame_count += 1
                if live_frame_count % 2 == 0:
                    raw_live = np.frombuffer(
                        fbo_out.read(components=3, dtype='f4'), dtype=np.float32
                    )
                    frame_live = (raw_live.reshape(H, W, 3) * 255.0).clip(0, 255).astype(np.uint8)
                    frame_live = np.flipud(frame_live)
                    live_writer.write(cv2.cvtColor(frame_live, cv2.COLOR_RGB2BGR))

            hud_surf = pygame.Surface(WIN_SIZE, pygame.SRCALPHA)
            hud_surf.fill((0, 0, 0, 0))
            draw_hud(hud_surf, state['mode_idx'], state['palette_idx'],
                     audio.bpm, val, bass, mid, high,
                     glow_on, feedback_on, audio.bpm_sync,
                     audio.beat_sensitivity, cinematic_on, active_preset,
                     tunnel_on=tunnel_on,
                     kick=kick, snare=snare, hihat=hihat, subbass=subbass,
                     autopilot_on=autopilot_on, autopilot_every_beats=autopilot_every_beats)

            # ── Renderiza HUD como overlay RGBA sobre o frame OpenGL ──
            hud_data = pygame.image.tostring(hud_surf, 'RGBA', True)  # True = flip OpenGL y
            hud_tex.write(hud_data)
            ctx.screen.use()
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            hud_tex.use(0)
            hprog['u_tex'].value = 0
            hvao.render()
            ctx.disable(moderngl.BLEND)

            pygame.display.flip()
            clock.tick(60)

    finally:
        if live_writer is not None:
            live_writer.release()
            print(Fore.YELLOW + Style.BRIGHT + f"  ⚠  Janela fechada durante gravação. Arquivo parcial: {live_tmp_path}")
        shared_panda[5] = 0.0
        audio.close()
        pygame.quit()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == 'render':
        if len(sys.argv) < 5:
            print("Uso: python fractal_visualizer.py render <audio> <preset> <output.mp4> [largura altura fps]")
            print(f"Presets disponíveis: {list(ALL_PRESETS.keys())}")
            sys.exit(1)
        _, _, audio_p, preset_n, out_p, *extras = sys.argv
        res = (int(extras[0]), int(extras[1])) if len(extras) >= 2 else (1280, 720)
        fps = int(extras[2]) if len(extras) >= 3 else 30
        render_offline(audio_p, preset_n, out_p, resolution=res, fps=fps)
    else:
        main()
