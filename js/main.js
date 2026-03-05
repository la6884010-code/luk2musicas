// ===== Modal Demo =====

const modal    = document.getElementById('demoModal');
const overlay  = document.getElementById('demoOverlay');
const closeBtn = document.getElementById('demoClose');

const triggers = [
  document.getElementById('nav-demo-btn'),
  document.getElementById('hero-demo-btn'),
  document.getElementById('pricing-demo-btn'),
];

function isMobile() {
  return window.innerWidth <= 768;
}

function openModal() {
  const content = document.querySelector('.demo-modal-content');
  const old = content.querySelector('.demo-modal-video, .demo-modal-iframe');
  if (old) old.remove();

  const iframe = document.createElement('iframe');
  iframe.src             = 'demo.html';
  iframe.className       = 'demo-modal-iframe';
  iframe.allow           = 'autoplay; microphone';
  iframe.allowFullscreen = true;
  content.appendChild(iframe);

  modal.classList.add('active');
  if (isMobile()) {
    modal.classList.add('mobile-fullscreen');
  }
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.remove('active');
  modal.classList.remove('mobile-fullscreen');
  document.body.style.overflow = '';
  const iframe = document.querySelector('.demo-modal-iframe');
  if (iframe) iframe.remove();
}

triggers.forEach(function(btn) {
  if (btn) btn.addEventListener('click', openModal);
});

closeBtn.addEventListener('click', closeModal);
overlay.addEventListener('click', closeModal);
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

/* ═══════════════════════════════════════
   BEAT LOOP ORGÂNICO — energia musical
═══════════════════════════════════════ */
(function beatLoop(){
  document.querySelectorAll('.pricing-col').forEach(col => {
    if (Math.random() < 0.35) {
      col.classList.add('isBeat');
      setTimeout(() => col.classList.remove('isBeat'), 160);
    }
  });
  setTimeout(beatLoop, 300 + Math.random()*400);
})();


/* ═══════════════════════════════════════
   PARALLAX SUAVE — mexe no wrapper (não no img)
   (pricing mascots + hero)
═══════════════════════════════════════ */
document.addEventListener('mousemove', (e) => {
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  const dx = (e.clientX - cx) / cx;
  const dy = (e.clientY - cy) / cy;

  const k2p = document.getElementById('k2Parallax');
  const jup = document.getElementById('juParallax');
  const hk2 = document.getElementById('heroK2');

  if (k2p) k2p.style.transform = `translate(${dx*5}px, ${dy*3}px)`;
  if (jup) jup.style.transform = `translate(${dx*-4}px, ${dy*3}px)`;

  /* heroK2 vai ser controlado pelo "look at preview" abaixo,
     então aqui só damos um empurrão bem pequeno (opcional) */
  // if (hk2) hk2.style.transform = `translate(${dx*1}px, ${dy*1}px)`;
});


/* ═══════════════════════════════════════
   HERO K2 "LOOK AT PREVIEW"
   K2 inclina e se aproxima conforme o mouse fica perto do preview
═══════════════════════════════════════ */
document.addEventListener('mousemove', (e) => {
  const preview = document.querySelector('.preview-video');
  const k2 = document.getElementById('heroK2');
  if (!preview || !k2) return;

  const rect = preview.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;

  const dx = e.clientX - centerX;
  const dy = e.clientY - centerY;
  const dist = Math.sqrt(dx*dx + dy*dy);

  const maxDist = 650; // área de influência
  const influence = Math.max(0, 1 - dist / maxDist);

  const tilt = (dx / 140) * influence;          // rotação leve
  const pullX = (dx / 220) * influence;         // aproximação leve
  const pullY = (dy / 260) * influence;

  k2.style.transform =
    `translate(${pullX}px, ${pullY}px) rotate(${tilt}deg)`;
});