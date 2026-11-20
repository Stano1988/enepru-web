(() => {
  const stage = document.getElementById('building-preview');
  const scene = stage.querySelector('.energy-schematic');
  const choices = stage.querySelector('.building-choices');
  const replay = stage.querySelector('.motion-replay');
  const estimateBuilding = document.getElementById('home-building');
  const motion = window.matchMedia('(prefers-reduced-motion: no-preference)');

  function select(building) {
    for (const button of choices.querySelectorAll('button')) {
      button.setAttribute('aria-pressed', String(button.dataset.buildingExample === building));
    }
    for (const model of scene.querySelectorAll('[data-building-model]')) {
      model.hidden = model.dataset.buildingModel !== building;
    }
  }

  let observer;
  function play() {
    if (!motion.matches) return;
    observer?.disconnect();
    stage.classList.remove('building-entrance');
    void scene.offsetWidth; // Apply the reset before restarting the CSS animation.
    stage.classList.add('building-entrance');
  }

  choices.hidden = false;
  choices.addEventListener('click', event => {
    const button = event.target.closest('[data-building-example]');
    if (!button) return;
    estimateBuilding.value = button.dataset.buildingExample;
    estimateBuilding.dispatchEvent(new Event('change'));
    play();
  });
  estimateBuilding.addEventListener('change', () => select(estimateBuilding.value));
  window.addEventListener('pageshow', () => select(estimateBuilding.value));
  select(estimateBuilding.value);
  replay.hidden = !motion.matches;
  replay.addEventListener('click', play);
  motion.addEventListener('change', event => {
    replay.hidden = !event.matches;
    if (!event.matches) stage.classList.remove('building-entrance');
  });
  if (motion.matches && 'IntersectionObserver' in window) {
    observer = new IntersectionObserver(([entry]) => {
      if (entry.intersectionRatio >= 0.45) play();
    }, {threshold: 0.45});
    observer.observe(scene);
  }
})();
