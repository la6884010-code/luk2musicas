# LUK2 Visualizer — Memória Completa do Projeto

## O que é o projeto
Landing page de venda + visualizador fractal de áudio em tempo real.
Produto comercial com versão FREE (download grátis) e PRO (em breve, via Hotmart, R$15/mês · $9,99/mês).

---

## ESTRUTURA DE ARQUIVOS

```
LUK2-Visualizer/
├── index.html                    ← Landing page de venda
├── demo.html                     ← Visualizador WebGL2 (abre em modal/iframe)
├── testes_validados.html         ← Lab interno de testes canvas 2D
├── didiyprincipalpagina2.0.py    ← App desktop Python v3.3 (produto principal)
├── didiy ao vivo.py              ← App desktop Python v2.0 (versão anterior)
├── index.html.txt                ← Rascunho histórico (lixo, só tem h1)
├── css/
│   └── styles.css                ← Todos os estilos da landing
├── js/
│   └── main.js                   ← JavaScript da landing (modal, parallax, beat)
├── assets/
│   ├── images/
│   │   ├── k2.png                ← Mascote K2 (robô ciano)
│   │   ├── ju.png                ← Mascote JU (personagem pink/magenta)
│   │   ├── LUK2(1).png           ← Screenshot do visualizador (galeria)
│   │   ├── luk2(3).png           ← Screenshot do visualizador (galeria)
│   │   └── luk2(4).jpg           ← Screenshot do visualizador (galeria)
│   ├── videos/
│   │   ├── LUK2.mp4              ← Preview do LUK2 PRO (card PRO, autoplay loop)
│   │   └── gravacao.mp4          ← Demo do visualizador (hero card, autoplay+controls)
│   └── audio/                    ← GITIGNORED — músicas de teste
│       ├── demo.mp3              ← Música padrão do demo
│       ├── futuristica.mp3
│       ├── guitarra.mp3
│       ├── guitarragrave.mp3
│       ├── guitarravozcltyr.mp3
│       ├── musica calma.mp3
│       ├── musica grave curto.mp3
│       ├── musica.mp3
│       ├── musica2.mp3
│       ├── musicas batidas.mp3
│       └── vozguitarragrave.mp3
├── memoria/
│   └── projeto.md                ← Este arquivo
├── .gitignore
└── .vscode/
    └── settings.json
```

---

## ARQUIVO: index.html — Landing Page Principal

### Seções em ordem
1. **Topbar** (sticky, blur backdrop): logo "L" gradiente, nome LUK2, tagline "O Futuro da Música Visual", nav com links Demo / Preços / Visualizar
2. **Hero**: título + parágrafo à esquerda; card com vídeo `gravacao.mp4` (preview do demo) à direita + mini-FAQ (3 perguntas) + mascote K2 flutuando com bolinha "Olha isso! 👀"
3. **Section #features**: 3 tiles — Presets, Exportação, Reação por Instrumento
4. **Section #download**: botão Google Drive (versão 1.1, Windows 64-bit, 84MB)
5. **Section .impact**: 4 itens — Separação por Instrumento, Câmera Cinematográfica, Render 4K Offline, Motor de Presets
6. **Section .gallery-section**: grid 3 colunas com 3 screenshots, legenda "Estudos visuais explorando o universo estético do LUK2"
7. **Section .criar-section**: "O que você pode criar com o LUK2" — 3 cards com ícones SVG inline: Visualizações reativas, Presets que respondem ao beat, Exportação em alta qualidade
8. **Section .pro-section**: badge "EM BREVE", título "LUK2 PRO", descrição, 6 features, preço R$15/mês · $9,99/mês, botão Hotmart, vídeo `LUK2.mp4` no lado direito
9. **Section #pricing**: 2 colunas — FREE (mascote K2, badge "GRÁTIS") e PRO (mascote JU, badge "PRO"). Parallax nos mascotes. Beat orgânico animado via JS
10. **Bloco Early Access**: botão "Entrar na Lista" → Mailchimp (eepurl.com/jAQY9I)
11. **Section #faq**: 2 perguntas básicas
12. **Footer**: © 2026 LUK2
13. **#demoModal**: modal com iframe para `demo.html`, ativado por 3 botões (nav, hero, pricing)

### JavaScript inline (no final do index.html)
- `pixelBurst(el)`: ao clicar nos mascotes K2, espalha 20 partículas coloridas (magenta/ciano/etc) com animação CSS
- **Parallax mouse**: `mousemove` move `k2Parallax`, `juParallax` e `heroK2` suavemente com o cursor
- **Beat loop**: `setTimeout` recursivo com intervalo aleatório 180-500ms, adiciona `.isBeat` por 130-170ms nos `.pricing-col`

### CSS inline embaixo de cada seção
- `.gallery-section`: fundo `linear-gradient(135deg, #000a1a, #0a0015)`, grid 3 colunas, cards com borda sutil
- `.criar-section`: fundo `linear-gradient(135deg, #0a0015, #000a1a)`, bordas magenta/ciano, hover translateY(-4px) + glow ciano
- `.pro-section`: fundo `linear-gradient(135deg, #0a0015, #000a20)`, layout flex 2 colunas, preço em magenta/ciano
- `.pro-preview-box`: max-width 380px, overflow hidden, vídeo 100% width
- **Mascotes (grande bloco CSS)**: `.hero-k2-wrap`, `.hero-k2`, `.hero-k2-bubble`, `.pricing-cols`, `.mascot-stage`, `.mascot-halo`, `.mascot-parallax`, `.mascot-img`, `.k2-img`, `.ju-img`, `.stage-platform`, `.price-card`, animações `k2-idle`, `ju-idle`, `k2-curious`, `ju-power`, `halo-k2`, `halo-ju`, `.isBeat`, `.pixel-burst`

---

## ARQUIVO: css/styles.css — Estilos Globais

### CSS Variables (`:root`)
- `--bg`: #000008
- `--panel`: rgba(255,255,255,0.04)
- `--panel2`: rgba(255,255,255,0.07)
- `--text`: rgba(255,255,255,0.95)
- `--muted`: rgba(255,255,255,0.58)
- `--stroke`: rgba(255,0,255,0.18)
- `--glow`: rgba(255,0,255,0.35)
- `--magenta`: #ff00ff
- `--cyan`: #00ffff
- `--grad`: linear-gradient(90deg, #ff00ff, #00ffff)

### Blocos principais
- `body::before`: background animado com 3 radial-gradients (magenta 22%, ciano 14%, roxo 16%), blur 60px, animação `luk2-float` 10s, z-index:-1
- `.topbar`: sticky top:0, flex space-between, border-bottom magenta, backdrop-filter blur(14px), background rgba(0,0,8,0.88)
- `.logo`: 44x44px, border-radius 14px, gradiente magenta→ciano, box-shadow neon duplo
- `.cta`: gradiente magenta→ciano, cor preta, box-shadow neon, hover scale(1.05)
- `.cta-big`: padding maior, font-size 15px
- `.ghost`: borda neon, fundo transparente, hover borda magenta
- `.hero`: grid 1.1fr / 0.9fr, max-width 1100px
- `.hero-left h1`: gradient 135deg branco→rosa→ciano, font-size 42px, weight 900
- `.card`: border-radius 18px, borda magenta 0.2, fundo 0.03, hover scale(1.015)
- `.hero-right .card`: overflow hidden, animação `luk2-card-pulse`, pseudo-elementos com glow
- `.preview-video`: 260px altura, border-radius 14px, hover opacity .82
- `.preview-badge`: posição absoluta top-right, cor magenta, blur backdrop
- `.section`: max-width 1100px
- `.grid`: 3 colunas, `.tile`: hover translateY(-4px) + glow ciano
- `.impact`: padding 80px, bg gradient escuro, grid 2x2, `.impact-item` com border-left magenta
- `.pricing`: bg gradient, `.price-card.pro` com gradiente magenta e box-shadow 70px
- `.badge`, `.pro-badge`: capsulas com letras maiúsculas
- `.price-list li::before`: ✦ em ciano
- `.early`: grid 1.1fr / 0.9fr, bg magenta 4%, borda magenta
- `.faq`: border-bottom separador, h3 em ciano
- `.demo-modal`: position fixed, overlay blur 8px, content max-width 820px, `.demo-modal-iframe` 520px altura
- **Animações**: `luk2-float` (translate 3D + scale), `luk2-card-pulse` (scale 1 → 1.008)
- **Responsivo**: 900px → 1 coluna, nav hidden; 768px → modal fullscreen; 600px → iframe 340px
- **Mascotes**: `mascot-breath` 4s, `mascot-blink` 7s, `.isBeat .mascot-img` scale(1.05) + glow
- `.mascot-shadow`: ellipse gradiente escuro, blur 4px, reage ao `.isBeat`
- `hero-k2-float` 3.8s (flutua livremente), `hero-k2-curious` no hover
- `pricing-k2-idle` 3.5s (ancorado, não flutua livre)

---

## ARQUIVO: js/main.js — JavaScript da Landing

### Modal Demo
```javascript
// Abre demo.html em iframe dentro do #demoModal
// Triggers: #nav-demo-btn, #hero-demo-btn, #pricing-demo-btn
function openModal()   // cria iframe, adiciona .active, mobile → .mobile-fullscreen
function closeModal()  // remove .active, destrói iframe (para o áudio)
// Fecha: botão × | clique no overlay | tecla ESC
```

### Beat Loop Orgânico
```javascript
// Intervalo aleatório 300-700ms
// 35% de chance por coluna de receber .isBeat
// .isBeat dura 160ms
(function beatLoop(){ ... setTimeout(beatLoop, 300 + Math.random()*400) })()
```

### Parallax Suave
```javascript
// mousemove → dx/dy normalizados -1..1
// k2Parallax: translate(dx*5px, dy*3px)
// juParallax: translate(dx*-4px, dy*3px) — oposto para profundidade
```

### Hero K2 "Look at Preview"
```javascript
// K2 inclina e se aproxima do preview conforme distância do mouse
// Área de influência: 650px de raio
// tilt = (dx/140) * influence (rotação leve)
// pullX/pullY = aproximação proporcional
```

---

## ARQUIVO: demo.html — Visualizador WebGL2

### UI / Layout
- Canvas WebGL2 fullscreen, position absolute
- `#hud` (topo): "LUK2" + "DEMO" + `#bpmDisplay`
- `#controls` (rodapé): track info + 8 barras de frequência + botões modo + swatches paleta
- `#startOverlay`: tela inicial, botão "INICIAR DEMO", drag-and-drop de áudio
- `#idleMsg`: mensagem central pulsante "▶ coloque sua música para começar"
- `#hint`: aparece após 3.5s, some após 9s — "Explore os MODOS e PALETAS abaixo"
- `#loadingMsg`: spinner durante carregamento
- `.watermark`: "LUK2 FREE DEMO" canto inferior direito
- `#beatFlash`: borda azul que pisca no beat

### Shaders GLSL (WebGL2 ES 300)
**Vertex Shader**: simples, passa `in_vert` → `v_uv`, full-screen quad

**Fragment Shader — uniforms:**
- `u_time` (float), `u_res` (vec2)
- `u_audio`, `u_beat`, `u_bass`, `u_mid`, `u_high`, `u_kick`, `u_snare` (floats 0..1)
- `u_color_offset` (float — desliza no beat)
- `u_palette` (int 0-4), `u_mode` (int 0-3)

**Fragment Shader — funções:**
- `aces(vec3)`: tonemapping ACES
- `pal(t, co, intensity)`: paleta coseno com 5 variações, saturação modulada por instrumento
- `rot2(vec2, float)`: rotação 2D
- `modeLoop(uv)`: 4 iterações de fract+rot, zoom por bass/beat/kick
- `modeTunnel(uv)`: coordenadas polares, profundidade por tempo+beat+bass
- `modeKaleid(uv)`: simetria (6 + floor(beat*6)) lados, zoom por bass+beat+kick
- `modePlasma(uv)`: senos sobrepostos, modulados por beat/mid/high/snare

**Fragment Shader — pipeline main():**
1. Camada bass: escala UV + rotação (respiração contínua)
2. Camada mid: flutter sinusoidal
3. Camada beat/kick: zoom reverso + tremor snare + shimmer high
4. Chama o modo visual
5. Glow reativo (col * beat * bass)
6. Divisão de bloom (length(col))
7. ACES tonemapping
8. Flash de beat (mix com paleta)
9. Flash de snare (mix com branco 40%)
10. Vignette radial suave

### Sistema de Áudio (Web Audio API)
```javascript
const FFT = 512           // bins — menor latência
analyser.smoothingTimeConstant = 0.0  // sem suavização interna
analyser.minDecibels = -90
analyser.maxDecibels = -10

// Bandas
function bandRMS(lo, hi)  // RMS de frequência lo..hi Hz
function band(lo, hi)     // média linear

// Beat detection — Spectral Flux
const FLUX_HIST = 43      // histórico de 43 frames
const BEAT_SENS = 1.5     // multiplicador de variância
const COOL_FRAMES = 8     // cooldown entre beats
// Threshold = avg + variance*BEAT_SENS, mínimo avg*1.8
// Só detecta no pico dominante (flux >= fluxPeak*0.95)

// BPM: média de até 8 intervalos entre beats
```

### Render Loop
```javascript
function render(ts) {
  requestAnimationFrame(render)
  // compensa outputLatency + baseLatency do browser
  const t = (ts - startT)/1000 + latency
  processAudio()           // lê FFT, calcula bandas, detecta beat
  // color offset desliza no beat
  // barras de frequência atualizadas (8 faixas)
  // uniforms enviados para GPU
  gl.drawArrays(gl.TRIANGLES, 0, 6)  // full-screen quad (6 vértices)
}
```

### Controles
- Botões `.mode-btn` (data-mode 0-3): trocam `mode`
- Swatches `.palette-swatch` (data-palette 0-4): trocam `palette`
- `M` = próximo modo, `P` = próxima paleta
- Drag & drop de arquivo de áudio → `loadFile()`
- `startBtn` → carrega `assets/audio/demo.mp3` → fallback OSC 80Hz se não encontrar

---

## ARQUIVO: testes_validados.html — Lab de Testes Canvas 2D

**Propósito**: arquivo interno para testar física de anéis e partículas antes de migrar pro produto.

### Configuração de Anéis
```javascript
const N_RINGS = 6
const RING_RADII   = [0.07, 0.13, 0.20, 0.28, 0.37, 0.47]  // fração do menor lado
const RING_COLORS  = ['0,255,255', '255,0,255', ...]         // ciano/magenta alternados
const RING_DELAY   = [0, 3, 6, 9, 12, 15]                   // delay em frames (ripple)
const RING_MAG     = [1.2, 1.6, 2.0, 2.5, 3.2, 4.0]        // magnitude crescente
```

### Estados Físicos
- `ringVel[6]`, `ringPos[6]`: velocidade e posição de cada anel
- `trailR[6]`, `trailA[6]`: trail (rastro) por anel
- `pendingKicks[6]`: fila de kicks com framesLeft e mag
- `breathPos/Vel`: expansão por bass (anéis 1-5)
- `wavePhase/Amp`: modulação por mid (anel 0 — guitarra/voz)
- `pulseVel/Pos`, `warpAmount`, `flowVel/Angle`: física calculada mas não renderizada (validada)
- `flashAlpha`, `glowStrength`, `trailRadius/Alpha`: efeitos de impacto
- `ghostData[]`: fantasmas de pulso anteriores em ciano (3 slots, alphas 0.70/0.40/0.15)
- `smoke[]`: partículas de fumaça neon (28 por kick)

### Funções principais
```javascript
applyKickImpulse(mag)  // flash, ghost, pulseVel, warpAmount, cascata de rings, spawn fumaça, scan ring
stepPhysics(rawBass, rawMid)  // processa kicks pendentes, física de molas, breath, wave, decaimentos
spawnSmoke(cx, cy, S)  // 28 partículas ao redor do anel 1
```

### Render (canvas 2D)
- Trail cinematográfico: `fillRect` rgba(0,0,0,0.14) — não limpa totalmente (deixa rastro)
- Bloom central radialGradient com hueShift
- Camada 1: 14 anéis orgânicos (folds=5, rot1) — hue progressivo
- Camada 2: 9 anéis (folds=7, rot2 oposto) — hue complementar
- 20 linhas radiais com glow
- Scan rings (círculos que expandem no kick)

### Beat Detection (idêntico ao demo.html)
- Spectral Flux com BEAT_SENS=2.0, COOL_FRAMES=14 (mais conservador)
- BPM estimado por intervalos de beat

---

## ARQUIVO: didiy ao vivo.py — Visualizador Python v2.0

**Dependências**: `pygame`, `moderngl`, `numpy`, `pyaudio`, `threading`, `queue`

### AudioAnalyzer
- Thread separada com `queue.Queue(maxsize=4)` — nunca bloqueia o render
- `find_loopback_device()`: busca WASAPI Loopback ou Stereo Mix, fallback para microfone
- FFT: `np.fft.rfft` com janela Hanning, CHUNK=1024
- Bandas: bass 20-140Hz, mid 140-4000Hz, high 4000-20000Hz (índices pré-calculados)
- Normalização adaptativa independente por banda (decay 0.995)
- Suavização assimétrica: subida rápida, decida lenta
- Beat detection: Spectral Flux focado em 20-140Hz (kick puro), threshold adaptativo, cooldown ~300ms, pico dominante
- BPM: média de até 8 intervalos

### Shaders GLSL (OpenGL 3.3)
Mesmos 4 modos e 5 paletas do demo.html, com pequenas diferenças:
- `u_travel`: velocidade de viagem no túnel (controlável pelo usuário)
- `u_vignette`: intensidade da vinheta (controlável)
- `u_glow`, `u_feedback`: flags booleanas
- `u_prev`: textura do frame anterior (para feedback)
- Distorção radial na main(): beat distorce UV + high tremula

### Post-processing
- `fbo_main`: render principal
- `fbo_glowA/B`: glow gaussiano ping-pong (blur horizontal + vertical)
- `fbo_prev`: armazena frame anterior para feedback
- Composite: mix(base, base+glow, glow_strength*0.5)
- Feedback: rot2(fbUV, 0.002+beat*0.005) * scale(0.985-bass*0.005) — zoom+rotação leve

### Controles
P/←→ paleta | M modo | V/↑↓ vinheta | G glow | F feedback | B BPM sync | [/] sensibilidade | +/- velocidade | SPACE freeze | ESC sair

---

## ARQUIVO: didiyprincipalpagina2.0.py — Visualizador Python v3.3

**Dependências**: tudo da v2.0 + `json`, `dataclasses`, `colorama`, `cv2` (opcional), `panda3d` (opcional)

### Sistema de Presets
```python
@dataclass
class Preset:
    name, mode, palette, glow, feedback, vignette, travel_speed, beat_sensitivity

# 5 presets de fábrica (imutáveis)
PRESETS_DEFAULT = {
    "default":      mode=0, palette=0, glow=True,  feedback=False, vignette=1.5, travel=0.3, sens=1.5
    "neon_tunnel":  mode=1, palette=1, glow=True,  feedback=True,  vignette=1.8, travel=0.7, sens=1.3
    "kaleid_dream": mode=2, palette=2, glow=True,  feedback=False, vignette=1.4, travel=0.2, sens=1.7
    "plasma_rave":  mode=3, palette=3, glow=True,  feedback=True,  vignette=1.2, travel=0.5, sens=1.2
    "aurora_loop":  mode=0, palette=4, glow=False, feedback=True,  vignette=2.0, travel=0.4, sens=1.6
}

# Presets do usuário salvos em presets.json (lista JSON)
# ALL_PRESETS = PRESETS_DEFAULT + USER_PRESETS mesclados
```

### Funções de Preset
```python
preset_to_dict(p)        # → dict para JSON
preset_from_dict(d)      # dict → Preset
load_user_presets(path)  # lê presets.json
save_user_presets(path)  # salva presets.json
is_factory_preset(name)  # verifica se é imutável
rebuild_all_presets()    # reconstrói ALL_PRESETS + PRESET_KEYS
```

### Controles extras vs v2.0
- `C`: câmera cinematográfica (zoom físico, paralaxe, movimento)
- `T`: túnel 3D Panda3D (thread separada, áudio compartilhado, requer panda3d)
- `R`: iniciar/parar gravação ao vivo com cv2 (requer opencv)
- `1-5`: presets rápidos diretos
- `Q/E`: anterior/próximo preset (navega ALL_PRESETS)
- `S`: salvar estado atual como preset do usuário em presets.json
- `X`: excluir preset do usuário ativo (fábrica: proibido)
- `BACKSPACE`: reset para presets LUK2 (apaga presets.json)
- `Y`: toggle autopilot
- `U/I`: aumentar/diminuir ciclo do autopilot (2→4→8→16 beats)
- `Z`: toggle BPM sync (era `B` na v2.0)

### Autopilot
- A cada N beats (configurável: 2, 4, 8, 16), troca pro próximo preset automaticamente
- Útil para performances ao vivo sem interação manual

---

## MASCOTES

### K2 (ciano/azul)
- Arquivo: `assets/images/k2.png` (PNG transparente, mix-blend-mode: screen)
- Representa: versão FREE / robozinho simpático
- Aparece: hero (flutuante ao lado do card), pricing coluna FREE
- Animações: `k2-idle`/`hero-k2-float` (flutua), `k2-curious` (curiosidade no hover), parallax leve
- Clique: efeito `pixelBurst` (20 partículas coloridas)
- Halo: radialGradient ciano rgba(0,200,255,0.28), animação `halo-k2`

### JU (magenta/pink)
- Arquivo: `assets/images/ju.png` (PNG transparente, maior que K2)
- Representa: versão PRO / personagem poderosa
- Aparece: pricing coluna PRO
- Animações: `ju-idle` (flutua), `ju-power` (poder no hover), parallax oposto ao K2
- Halo: radialGradient magenta rgba(255,0,200,0.45), animação `halo-ju` (mais intensa)
- Filter: `drop-shadow(0 0 40px rgba(255,0,200,0.95))` — muito mais brilhante que K2

---

## PALETAS DE COR (5) — usadas em TODOS os visualizadores

| # | Nome        | Característica                              |
|---|-------------|---------------------------------------------|
| 0 | Gelo→Fogo   | Muda dinamicamente com a intensidade do áudio (azul frio → laranja/fogo) |
| 1 | Neon        | Magenta/ciano, saturação cresce com bass/high |
| 2 | Pastel      | Suave, levemente modulada por mid/high      |
| 3 | Psicodélica | Muito saturada, modulada por bass/high      |
| 4 | Aurora Boreal | Verde/azul/turquesa, modulada por bass/high |

**Fórmula coseno** (Inigo Quilez): `a + b * cos(2π * (c*t + d))`

---

## MODOS VISUAIS (4) — em TODOS os visualizadores

| # | Nome              | Técnica                                     |
|---|-------------------|---------------------------------------------|
| 0 | Loop Fractal      | 4 iterações de fract(uv*1.5) + rot2, distância como brilho |
| 1 | Tunnel            | Coordenadas polares (r, θ), profundidade por tempo+beat |
| 2 | Kaleidoscópio     | Simetria N lados (6 + beat*6), fract iterativo |
| 3 | Plasma Orgânico   | Somas de senos 2D sobrepostos, modulados por mid/beat/high |

---

## FLUXO DO USUÁRIO

```
index.html
  └── clica "Demo" / "Ver demo" / "Testar o Demo"
        └── modal #demoModal abre
              └── demo.html carregado em <iframe>
                    └── clica "INICIAR DEMO"
                          └── Web Audio API inicializa
                                └── demo.mp3 carrega de assets/audio/
                                      └── visualizador WebGL2 começa
                                            ├── pode trocar MODO (M ou botões)
                                            ├── pode trocar PALETA (P ou swatches)
                                            └── pode arrastar música própria

  └── clica "Visualizar" / "Baixar Grátis"
        └── redirect Google Drive (versão 1.1, 84MB, Windows 64-bit)

  └── clica "Obter Pro" / "Quero Acesso Antecipado"
        └── redirect Hotmart (go.hotmart.com/O104759492I)

  └── clica "Entrar na Lista"
        └── redirect Mailchimp (eepurl.com/jAQY9I)
```

---

## LINKS IMPORTANTES

- Download gratuito: `https://drive.google.com/file/d/1uAaUj0NLOrBJ1hyEz4DgEdSQg5QfrGda/view?usp=drive_link`
- Hotmart PRO: `https://go.hotmart.com/O104759492I`
- Lista de e-mail: `http://eepurl.com/jAQY9I`
- Versão atual: 1.1 · Windows 64-bit · 84MB
- Preço PRO: R$15/mês (BR) · $9,99/mês (INT)
- Copyright: © 2026 LUK2

---

## GITIGNORE

```
testes_validados.html   ← arquivo de lab, não vai pro git
assets/audio/           ← pasta inteira ignorada
*.mp3, *.wav, *.ogg, *.flac, *.aac, *.m4a   ← áudios ignorados
```

---

## .VSCODE/SETTINGS.JSON

Configuração residual — referencia `js/main.js` como projeto Python (incorreto, artefato do VSCode).

---

*Atualizado: 2026-03-13*
