export function detectEdges(imageData, width, height) {
  const source = imageData.data;
  const luminance = new Float32Array(width * height);
  const edges = new Float32Array(width * height);

  for (let index = 0; index < width * height; index += 1) {
    const offset = index * 4;
    const alpha = source[offset + 3] / 255;
    luminance[index] = alpha <= 0.02
      ? 0
      : (source[offset] * 0.299 + source[offset + 1] * 0.587 + source[offset + 2] * 0.114) * alpha;
  }

  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const index = y * width + x;
      const gx =
        -luminance[index - width - 1] + luminance[index - width + 1] +
        -2 * luminance[index - 1] + 2 * luminance[index + 1] +
        -luminance[index + width - 1] + luminance[index + width + 1];
      const gy =
        -luminance[index - width - 1] - 2 * luminance[index - width] - luminance[index - width + 1] +
        luminance[index + width - 1] + 2 * luminance[index + width] + luminance[index + width + 1];
      edges[index] = Math.min(1, Math.hypot(gx, gy) / 420);
    }
  }

  return edges;
}
