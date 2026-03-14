# LUK2 Visualizer — Memória do Projeto

*Atualizado: 2026-03-14*

---

## O que é o projeto

Landing page de venda + visualizador fractal de áudio em tempo real.
Produto comercial com versão FREE (download grátis) e PRO (em breve, via Hotmart, R$15/mês · $9,99/mês).

---

## Repositório

- GitHub: `la6884010-code/luk2musicas` · branch `main`

---

## Estrutura de arquivos

```
LUK2-Visualizer/
├── index.html                    ← Landing page de venda
├── demo.html                     ← Visualizador WebGL2 (demo online, abre em modal)
├── didiyprincipalpagina2.0.py    ← App desktop Python v3.3 (produto principal)
├── didiy ao vivo.py              ← App desktop Python v2.0 (versão anterior, obsoleta)
├── luk2.spec                     ← Spec PyInstaller para build do .exe
├── requirements.txt              ← Dependências Python do projeto
├── css/styles.css                ← Estilos globais da landing
├── js/main.js                    ← JavaScript da landing (modal, parallax, beat)
├── assets/
│   ├── images/                   ← k2.png, ju.png, screenshots do visualizador
│   ├── videos/                   ← LUK2.mp4 (PRO preview), gravacao.mp4 (hero), borboleta.mp4 (calm)
│   └── audio/                    ← GITIGNORED — músicas de teste
├── memoria/
│   └── projeto.md                ← Este arquivo
└── .gitignore
```

---

## Versão atual em produção

- Release: **v1.2.0**
- Asset: `LUK2-v1.2.0.zip` (ZIP da pasta dist/LUK2/)
- Link direto: `https://github.com/la6884010-code/luk2musicas/releases/download/v1.2.0/LUK2-v1.2.0.zip`
- Botão "Baixar Grátis — Windows" na landing aponta para esse link

---

## Build do executável Windows

```bash
# Instalar dependências
pip install -r requirements.txt

# Gerar build
python -m PyInstaller luk2.spec

# Resultado em:
dist/LUK2/LUK2.exe
dist/LUK2/_internal/
```

Pastas `dist/`, `build/`, `*.zip`, `__pycache__/` estão no `.gitignore` — não vão pro git.

Para publicar nova versão:
1. Gerar build com PyInstaller
2. Zipar `dist/LUK2/` → `LUK2-vX.X.X.zip`
3. Criar release no GitHub via API (precisa de token `ghp_...`)
4. Fazer upload do ZIP como asset da release
5. Atualizar href do botão no index.html

---

## Fluxo do app desktop (v3.3 — estado atual)

1. Usuário abre `LUK2.exe`
2. Terminal mostra menu de controles (teclas disponíveis)
3. **Janela nativa do Windows abre** (`tkinter.filedialog`) para escolher a música
4. Usuário seleciona um `.mp3` ou `.wav`
5. Visualizador fractal inicia com OpenGL 3.3

---

## O que foi feito em 2026-03-14 (hoje)

### Landing page (index.html)

- **Seção PRO reformulada**: substituído preview estático por dois cards empilhados
  - Card superior: **Modo Energy** — vídeo `LUK2.mp4`, borda/glow magenta
  - Card inferior: **Modo Calm** — vídeo `borboleta.mp4`, borda/glow ciano, overlay suave
  - Labels flutuantes com backdrop-filter blur, dot colorido por modo
- **Subtítulo PRO atualizado**: "Do impacto psicodélico à fluidez do modo calm, sem limites e sem marca d'água"
- **Lista de benefícios PRO** reordenada: Energy antes de Calm
- **Botão de download corrigido**: era link Google Drive (pedia login), agora aponta para GitHub Releases
- **Mensagem de compatibilidade** adicionada abaixo do botão: "Baixe no seu PC ou notebook Windows • 64-bit"
- **Mensagem de confiança** adicionada: "✔ Download seguro"
- **Versão atualizada** na página: 1.2 · Windows 64-bit · 85MB

### App desktop (didiyprincipalpagina2.0.py)

- **`_base_dir()`**: nova função que resolve paths corretamente tanto em script Python quanto em .exe PyInstaller (usa `sys.executable` quando frozen, não `__file__`)
- **`PRESETS_JSON_PATH`**: agora usa `_base_dir()` — presets.json é salvo ao lado do .exe
- **`pick_audio_file()`**: substituída completamente
  - Antes: buscava mp3 na pasta com `os.walk` e pedia input() no terminal
  - Depois: abre janela nativa do Windows (`tkinter.filedialog.askopenfilename`)
- **Startup protegido**: try/except em pygame.init(), create_context(), FileAudioAnalyzer e compilação de shaders — erros exibem mensagem clara e aguardam ENTER
- **OpenGL**: mensagem explícita se GPU não suporta OpenGL 3.3 ou GLSL 330
- **`multiprocessing.freeze_support()`** adicionado no entry point (evita deadlock do Panda3D no .exe)
- **`import sys`** movido para o topo do módulo

### Arquivos de build criados

- **`requirements.txt`**: lista oficial de dependências (pygame, moderngl, numpy, colorama, soundfile, PyInstaller)
- **`luk2.spec`**: spec PyInstaller com hiddenimports corretos (soundfile, numpy, pygame, moderngl, tkinter, tkinter.filedialog, multiprocessing), console=True (obrigatório por usar tkinter no terminal)

### Infraestrutura

- **`.gitignore` atualizado**: adicionado `dist/`, `build/`, `*.zip`, `__pycache__/`, `*.pyc`
- **Release v1.2.0** criada no GitHub via API
- **ZIP publicado** como asset da release via API do GitHub

---

## Regras de colaboração (como trabalhamos)

- Claude faz tudo que puder automaticamente (editar código, rodar comandos, commit, push, upload de release)
- Usuário só é acionado para o que for impossível sem intervenção humana (abrir programas, autenticar no browser, etc.)
- Sempre fazer commit + push automaticamente após qualquer alteração
- Questionar antes de agir quando o elemento/texto alvo não existir ou houver ambiguidade

---

## Links importantes

- Download FREE: GitHub Releases v1.2.0 (ZIP)
- Hotmart PRO: `https://go.hotmart.com/O104759492I`
- Lista de e-mail: `http://eepurl.com/jAQY9I`
- Preço PRO: R$15/mês (BR) · $9,99/mês (INT)
- Copyright: © 2026 LUK2
