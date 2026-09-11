import { detectEdges } from "./edgeDetector.js";
import { enhanceEdgesWithOpenCV } from "./openCvEnhancer.js";

export async function samplePortrait(image, canvas, options = {}) {
  const sampleWidth = options.sampleWidth || 420;
  const ratio = image.naturalHeight / image.naturalWidth;
  const width = sampleWidth;
  const height = Math.max(1, Math.round(sampleWidth * ratio));
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  canvas.width = width;
  canvas.height = height;
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);

  const imageData = ctx.getImageData(0, 0, width, height);
  const fallbackEdges = detectEdges(imageData, width, height);
  const opencvEdges = await enhanceEdgesWithOpenCV(imageData, width, height);
  const edges = opencvEdges ? blendEdges(fallbackEdges, opencvEdges) : fallbackEdges;

  return { imageData, edges, width, height, edgeSource: opencvEdges ? "opencv" : "fallback" };
}

function blendEdges(fallbackEdges, opencvEdges) {
  const result = new Float32Array(fallbackEdges.length);

  for (let index = 0; index < result.length; index += 1) {
    result[index] = Math.min(1, fallbackEdges[index] * 0.55 + opencvEdges[index] * 0.72);
  }

  return result;
}

export function readPixel(imageData, index) {
  const data = imageData.data;
  const offset = index * 4;
  return {
    r: data[offset],
    g: data[offset + 1],
    b: data[offset + 2],
    a: data[offset + 3] / 255,
  };
}
