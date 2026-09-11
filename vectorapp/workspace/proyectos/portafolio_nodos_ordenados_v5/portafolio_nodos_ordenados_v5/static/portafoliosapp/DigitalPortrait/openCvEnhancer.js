const OPENCV_TIMEOUT_MS = 3200;

async function waitForOpenCV() {
  const readyPromise = window.__opencvReady;

  if (readyPromise && typeof readyPromise.then === "function") {
    await Promise.race([
      readyPromise,
      new Promise((_, reject) => window.setTimeout(() => reject(new Error("OpenCV timeout")), OPENCV_TIMEOUT_MS)),
    ]);
  }

  if (!window.cv) return null;
  const cv = typeof window.cv.then === "function" ? await window.cv : window.cv;
  return cv && cv.Mat ? cv : null;
}

export async function enhanceEdgesWithOpenCV(imageData, width, height) {
  let cv = null;
  try {
    cv = await waitForOpenCV();
  } catch (error) {
    return null;
  }

  if (!cv) return null;

  let source = null;
  let gray = null;
  let blurred = null;
  let canny = null;
  let dilated = null;
  let kernel = null;

  try {
    source = cv.matFromImageData(imageData);
    gray = new cv.Mat();
    blurred = new cv.Mat();
    canny = new cv.Mat();
    dilated = new cv.Mat();
    kernel = cv.Mat.ones(2, 2, cv.CV_8U);

    cv.cvtColor(source, gray, cv.COLOR_RGBA2GRAY);
    cv.GaussianBlur(gray, blurred, new cv.Size(3, 3), 0, 0, cv.BORDER_DEFAULT);
    cv.Canny(blurred, canny, 42, 118);
    cv.dilate(canny, dilated, kernel);

    const result = new Float32Array(width * height);
    const data = dilated.data;
    for (let index = 0; index < result.length; index += 1) {
      result[index] = data[index] / 255;
    }

    return result;
  } catch (error) {
    return null;
  } finally {
    if (source) source.delete();
    if (gray) gray.delete();
    if (blurred) blurred.delete();
    if (canny) canny.delete();
    if (dilated) dilated.delete();
    if (kernel) kernel.delete();
  }
}
