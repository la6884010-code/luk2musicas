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