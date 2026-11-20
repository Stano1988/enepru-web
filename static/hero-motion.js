(() => {
  const home = document.getElementById('uvod');
  const stage = home.querySelector('.home-stage');
  const motion = window.matchMedia('(prefers-reduced-motion: no-preference)');

  if (!motion.matches || !('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver(([entry]) => {
    if (home.hidden || entry.intersectionRatio < 0.25) return;
    stage.classList.add('home-stage-entrance');
    observer.disconnect();
  }, {threshold: 0.25});

  observer.observe(stage);

  document.addEventListener('site:routechange', () => {
    if (home.hidden) stage.classList.remove('home-stage-entrance');
  });
})();
