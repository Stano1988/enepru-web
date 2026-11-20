(() => {
  const home = document.getElementById('uvod');
  const stage = home.querySelector('.home-stage');
  const scene = stage.querySelector('.home-scene');
  const replay = stage.querySelector('.motion-replay');
  const motion = window.matchMedia('(prefers-reduced-motion: no-preference)');

  if (!motion.matches) return;

  let observer;
  function play() {
    observer?.disconnect();
    stage.classList.remove('home-stage-awaiting', 'home-stage-entrance');
    void scene.offsetWidth; // Commit the reset before starting a new CSS animation.
    stage.classList.add('home-stage-entrance');
  }

  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(([entry]) => {
      if (home.hidden || entry.intersectionRatio < 0.45) return;
      play();
    }, {threshold: 0.45});
    stage.classList.add('home-stage-awaiting');
    observer.observe(scene);
  }

  replay.hidden = false;
  replay.addEventListener('click', play);
  document.addEventListener('site:routechange', () => {
    if (home.hidden) stage.classList.remove('home-stage-entrance');
  });
})();
