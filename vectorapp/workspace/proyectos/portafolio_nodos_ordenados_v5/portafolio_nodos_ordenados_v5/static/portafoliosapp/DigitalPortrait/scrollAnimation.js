export function createScrollController(section, onProgress) {
  let ticking = false;
  let current = 0;

  function calculateProgress() {
    const rect = section.getBoundingClientRect();
    const scrollable = Math.max(1, section.offsetHeight - window.innerHeight);
    return Math.max(0, Math.min(1, -rect.top / scrollable));
  }

  function update() {
    ticking = false;
    current = calculateProgress();
    onProgress(current);
  }

  function requestUpdate() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(update);
  }

  window.addEventListener("scroll", requestUpdate, { passive: true });
  window.addEventListener("resize", requestUpdate);
  requestUpdate();

  return {
    destroy() {
      window.removeEventListener("scroll", requestUpdate);
      window.removeEventListener("resize", requestUpdate);
    },
    get progress() {
      return current;
    },
  };
}
