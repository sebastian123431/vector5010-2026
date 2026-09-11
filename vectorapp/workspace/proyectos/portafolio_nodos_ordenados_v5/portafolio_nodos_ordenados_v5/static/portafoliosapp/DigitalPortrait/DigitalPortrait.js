import { samplePortrait } from "./imageSampler.js";
import { generateGraph } from "./graphGenerator.js";
import { GraphRenderer } from "./graphRenderer.js";

const animeDriver = window.anime || {
  timeline: () => ({ seek: () => {}, add: () => ({}) }),
};

function setPortraitMask(stage, progress) {
  const visualProgress = normalizeProgress(progress);
  const boundary = 8 + visualProgress * 112;
  stage.style.setProperty("--digital-progress", visualProgress.toFixed(3));
  stage.style.setProperty("--portrait-progress", `${boundary.toFixed(2)}%`);
  stage.style.setProperty("--portrait-saturate", Math.max(0.42, 1 - visualProgress * 0.52).toFixed(3));
  stage.style.setProperty("--portrait-contrast", (1 + visualProgress * 0.1).toFixed(3));
  stage.style.setProperty("--frame-opacity", (0.18 + visualProgress * 0.5).toFixed(3));
  const pulseOpacity = 0.18 + visualProgress * 0.38;
  stage.parentElement?.style.setProperty("--pulse-opacity", pulseOpacity.toFixed(3));
  stage.parentElement?.style.setProperty("--pulse-opacity-soft", (pulseOpacity * 0.65).toFixed(3));
}

function normalizeProgress(progress) {
  return progress >= 0.965 ? 1 : Math.max(0, Math.min(1, progress));
}

function fitImageToStage(image, stage) {
  const imageRatio = image.naturalWidth / image.naturalHeight;
  stage.style.aspectRatio = imageRatio > 0 ? `${image.naturalWidth} / ${image.naturalHeight}` : "0.83";
}

async function loadPortrait(image) {
  if (image.complete && image.naturalWidth > 0) return image;
  await new Promise((resolve, reject) => {
    image.addEventListener("load", resolve, { once: true });
    image.addEventListener("error", reject, { once: true });
  });
  return image;
}

function createTimeline(state) {
  return animeDriver.timeline({
    autoplay: true,
    loop: true,
    direction: "alternate",
    duration: 1000,
    easing: "easeInOutSine",
    update: () => {
      state.onUpdate?.(state.progress);
    },
  }).add({
    targets: state,
    progress: [0, 1],
    duration: 5200,
    easing: "easeInOutSine",
  });
}

function updateReadout(root, progress) {
  const label = root.querySelector("[data-progress-label]");
  if (label) label.textContent = `${Math.round(normalizeProgress(progress) * 100)}%`;
}

function performanceProfile() {
  const memory = navigator.deviceMemory || 8;
  const cores = navigator.hardwareConcurrency || 8;
  const mobile = window.innerWidth < 760;
  const lite = mobile || memory <= 4 || cores <= 4;

  return {
    lite,
    sampleWidth: lite ? 300 : 400,
    maxNodes: lite ? 520 : 980,
    fps: lite ? 24 : 42,
  };
}

async function boot(root) {
  const stage = root.querySelector(".portrait-stage");
  const image = root.querySelector(".portrait");
  const graphCanvas = root.querySelector(".graph");
  const analysisCanvas = root.querySelector(".analysis-canvas");
  const state = {
    progress: 0,
    onUpdate: (progress) => {
      setPortraitMask(stage, progress);
      updateReadout(root, progress);
    },
  };
  const renderer = new GraphRenderer(graphCanvas, stage);
  const profile = performanceProfile();
  let running = true;
  let visible = true;
  let lastFrameTime = 0;

  try {
    await loadPortrait(image);
  } catch (error) {
    stage.classList.add("is-missing");
    setPortraitMask(stage, 0);
    renderer.resize();
    return;
  }

  stage.classList.remove("is-missing");
  fitImageToStage(image, stage);
  renderer.resize();

  const sample = await samplePortrait(image, analysisCanvas, {
    sampleWidth: profile.sampleWidth,
  });
  renderer.setGraph(generateGraph(sample, { maxNodes: profile.maxNodes }));
  createTimeline(state);

  const renderLoop = (time) => {
    if (!running) return;
    const frameInterval = 1000 / profile.fps;
    if (visible && time - lastFrameTime >= frameInterval) {
      renderer.render(normalizeProgress(state.progress), time);
      lastFrameTime = time;
    }
    requestAnimationFrame(renderLoop);
  };

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      renderer.resize();
      setPortraitMask(stage, state.progress);
    }, 180);
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting);
    }, { threshold: 0.05 });
    observer.observe(root);
  }

  document.addEventListener("visibilitychange", () => {
    running = !document.hidden;
    if (running) requestAnimationFrame(renderLoop);
  });

  requestAnimationFrame((time) => {
    renderer.resize();
    setPortraitMask(stage, state.progress);
      renderer.render(normalizeProgress(state.progress), time);
  });

  requestAnimationFrame(renderLoop);
}

document.querySelectorAll("[data-digital-portrait]").forEach((root) => {
  boot(root);
});
