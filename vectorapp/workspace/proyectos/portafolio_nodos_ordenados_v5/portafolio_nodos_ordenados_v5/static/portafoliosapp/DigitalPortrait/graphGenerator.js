import { readPixel } from "./imageSampler.js";

function randomFrom(seed) {
  let value = seed % 2147483647;
  return () => {
    value = value * 16807 % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function revealValue(nx, ny) {
  return Math.max(0, Math.min(0.92, (ny * 0.68) + ((1 - nx) * 0.34) - 0.04));
}

function colorFromPixel(pixel, edge, random) {
  const lift = 42 + edge * 62;
  const r = Math.min(255, Math.round(pixel.r * 0.66 + lift));
  const g = Math.min(255, Math.round(pixel.g * 0.66 + lift));
  const b = Math.min(255, Math.round(pixel.b * 0.66 + lift + random() * 14));
  return `rgb(${r}, ${g}, ${b})`;
}

function localContrast(imageData, width, height, x, y, centerLum) {
  const points = [
    [x - 2, y],
    [x + 2, y],
    [x, y - 2],
    [x, y + 2],
  ];
  let contrast = 0;

  points.forEach(([px, py]) => {
    if (px < 0 || py < 0 || px >= width || py >= height) return;
    const pixel = readPixel(imageData, py * width + px);
    if (pixel.a < 0.08) return;
    const lum = (pixel.r * 0.299 + pixel.g * 0.587 + pixel.b * 0.114) / 255;
    contrast = Math.max(contrast, Math.abs(centerLum - lum));
  });

  return contrast;
}

function regionWeight(nx, ny) {
  const cap = ny < 0.31 ? 0.24 : 0;
  const visor = nx > 0.42 && ny > 0.22 && ny < 0.38 ? 0.15 : 0;
  const capSide = nx > 0.18 && nx < 0.86 && ny > 0.08 && ny < 0.36 ? 0.14 : 0;
  const face = nx > 0.2 && nx < 0.8 && ny > 0.2 && ny < 0.57 ? 0.12 : 0;
  const neck = nx > 0.28 && nx < 0.72 && ny > 0.52 && ny < 0.66 ? 0.08 : 0;
  const jacket = ny > 0.62 ? 0.045 : 0;
  const shoulder = ny > 0.7 && (nx < 0.36 || nx > 0.64) ? 0.055 : 0;
  const center = Math.max(0, 0.09 - Math.abs(nx - 0.5) * 0.14);
  const clothingCenter = ny > 0.58 ? Math.max(0, 0.022 - Math.abs(nx - 0.5) * 0.05) : 0;
  return cap + visor + capSide + face + neck + jacket + shoulder + center + clothingCenter;
}

function graphRegion(nx, ny, type) {
  if (type === "cap") return "cap";
  if (ny > 0.62) return "clothing";
  if (ny > 0.52) return "neck";
  return "face";
}

export function generateGraph(sample, options = {}) {
  const random = randomFrom(92821);
  const { imageData, edges, width, height } = sample;
  const maxNodes = options.maxNodes || (window.innerWidth < 760 ? 520 : 980);
  const stride = Math.max(2, Math.round(Math.sqrt((width * height) / (maxNodes * 2.05))));
  const candidates = [];

  for (let y = 3; y < height - 3; y += stride) {
    for (let x = 3; x < width - 3; x += stride) {
      const index = y * width + x;
      const pixel = readPixel(imageData, index);
      if (pixel.a < 0.08) continue;

      const edge = edges[index];
      const luminance = (pixel.r * 0.299 + pixel.g * 0.587 + pixel.b * 0.114) / 255;
      const contrast = localContrast(imageData, width, height, x, y, luminance);
      const nxBase = x / width;
      const nyBase = y / height;
      const darkStructure = Math.max(0, (0.52 - luminance) * 0.54);
      const alphaNeighbors = [
        readPixel(imageData, index - 1).a,
        readPixel(imageData, index + 1).a,
        readPixel(imageData, index - width).a,
        readPixel(imageData, index + width).a,
      ];
      const alphaEdge = alphaNeighbors.some((value) => value < 0.08) ? 0.72 : 0;
      const structure = Math.max(edge, contrast * 1.75, alphaEdge, darkStructure);
      const weight = regionWeight(nxBase, nyBase);
      const density = Math.min(1, structure + weight);
      const clothingZone = nyBase > 0.58;
      const capZone = nyBase < 0.36 && nxBase > 0.12 && nxBase < 0.9;
      const faceZone = nxBase > 0.22 && nxBase < 0.78 && nyBase > 0.18 && nyBase < 0.56;
      const neckZone = nxBase > 0.28 && nxBase < 0.72 && nyBase > 0.52 && nyBase < 0.66;
      const faceFeature = faceZone && (edge > 0.075 || contrast > 0.058 || darkStructure > 0.11);
      const clothingFeature = clothingZone && (alphaEdge > 0 || edge > 0.17 || contrast > 0.14 || darkStructure > 0.23);
      const faceSurface = faceZone && !faceFeature && luminance > 0.32 && luminance < 0.86;
      const neckSurface = neckZone && !faceFeature && !clothingFeature && luminance > 0.28;
      const flatChance = pixel.a > 0.72 ? (capZone ? 0.08 : clothingZone ? 0.014 : faceZone ? 0.04 : 0.04) : 0.014;
      const threshold = clothingFeature ? 0.17 : faceFeature || capZone ? 0.09 : faceSurface || neckSurface ? 0.135 : clothingZone ? 0.3 : 0.15;
      const randomKeep = flatChance + density * (clothingFeature ? 0.22 : faceFeature || capZone ? 0.44 : faceSurface || neckSurface ? 0.18 : clothingZone ? 0.055 : 0.2);
      const keep = density > threshold || random() < randomKeep;

      if (!keep) continue;

      const jitterX = (random() - 0.5) * stride * 0.72;
      const jitterY = (random() - 0.5) * stride * 0.72;
      const nx = Math.max(0, Math.min(1, (x + jitterX) / width));
      const ny = Math.max(0, Math.min(1, (y + jitterY) / height));
      const type = faceSurface
        ? "face-surface"
        : neckSurface
        ? "neck-surface"
        : clothingZone && !clothingFeature
        ? "clothing-surface"
        : capZone && luminance < 0.55 && !faceFeature
        ? "cap"
        : alphaEdge > 0 ? "silhouette" : faceFeature || edge > 0.18 || contrast > 0.13 ? "feature" : luminance < 0.42 ? "dark" : "surface";
      const region = graphRegion(nx, ny, type);

      candidates.push({
        nx,
        ny,
        edge,
        density,
        contrast,
        luminance,
        type,
        region,
        reveal: revealValue(nx, ny),
        radius: 0.28 + density * 1.0 + (type === "face-surface" || type === "neck-surface" ? random() * 0.16 : type === "surface" || type === "clothing-surface" ? random() * 0.14 : type === "cap" ? random() * 0.36 : random() * 0.46),
        opacity: 0.18 + density * 0.5 + (type === "face-surface" || type === "neck-surface" ? random() * 0.07 : type === "surface" || type === "clothing-surface" ? random() * 0.04 : random() * 0.12),
        color: colorFromPixel(pixel, edge, random),
        driftX: (random() - 0.5) * (type === "surface" || type === "clothing-surface" ? 5 : type === "cap" ? 10 : 14),
        driftY: (random() - 0.5) * (type === "surface" || type === "clothing-surface" ? 5 : type === "cap" ? 10 : 14),
        phase: random() * Math.PI * 2,
        speed: 0.35 + random() * 0.8,
      });
    }
  }

  const nodes = candidates
    .sort((a, b) => b.density - a.density)
    .slice(0, maxNodes)
    .sort((a, b) => a.reveal - b.reveal);

  return {
    nodes,
    connections: connectNodes(nodes),
  };
}

function connectNodes(nodes) {
  const connections = [];
  const maxConnections = window.innerWidth < 760 ? 2 : 3;
  const connectionDistance = window.innerWidth < 760 ? 0.064 : 0.058;
  const counts = new Map();
  const buckets = new Map();
  const bucketSize = connectionDistance;

  nodes.forEach((node, index) => {
    const bx = Math.floor(node.nx / bucketSize);
    const by = Math.floor(node.ny / bucketSize);
    const key = `${bx}:${by}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(index);
  });

  nodes.forEach((node, index) => {
    const neighbors = [];
    const bx = Math.floor(node.nx / bucketSize);
    const by = Math.floor(node.ny / bucketSize);

    for (let oy = -1; oy <= 1; oy += 1) {
      for (let ox = -1; ox <= 1; ox += 1) {
        const bucket = buckets.get(`${bx + ox}:${by + oy}`) || [];
        bucket.forEach((otherIndex) => {
          if (otherIndex <= index) return;
          const target = nodes[otherIndex];
          const dx = node.nx - target.nx;
          const dy = node.ny - target.ny;
          const distance = Math.hypot(dx, dy);
          if (distance <= connectionDistance) {
            neighbors.push({ index: otherIndex, distance });
          }
        });
      }
    }

    neighbors
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 7)
      .forEach((neighbor) => {
        const fromCount = counts.get(index) || 0;
        const toCount = counts.get(neighbor.index) || 0;
        if (fromCount >= maxConnections || toCount >= maxConnections) return;
        const target = nodes[neighbor.index];
        if (!canConnectRegions(node, target, neighbor.distance, connectionDistance)) return;
        const bothSurface = (node.type === "surface" || node.type === "clothing-surface") && (target.type === "surface" || target.type === "clothing-surface");
        const capConnection = node.type === "cap" || target.type === "cap";
        if (bothSurface && neighbor.distance > connectionDistance * 0.52) return;
        if ((node.type === "clothing-surface" || target.type === "clothing-surface") && neighbor.distance > connectionDistance * 0.36) return;
        if (capConnection && neighbor.distance > connectionDistance * 0.82) return;
        counts.set(index, fromCount + 1);
        counts.set(neighbor.index, toCount + 1);
        connections.push({
          from: index,
          to: neighbor.index,
          reveal: Math.max(node.reveal, nodes[neighbor.index].reveal) + 0.05,
          strength: 1 - neighbor.distance / connectionDistance,
        });
      });
  });

  return connections;
}

function canConnectRegions(node, target, distance, connectionDistance) {
  if (node.region === target.region) return true;

  const regions = new Set([node.region, target.region]);
  const faceToClothing = regions.has("face") && regions.has("clothing");
  const capToClothing = regions.has("cap") && regions.has("clothing");
  const capToNeck = regions.has("cap") && regions.has("neck");

  if (faceToClothing || capToClothing || capToNeck) return false;

  if (regions.has("neck") && regions.has("clothing")) {
    return distance < connectionDistance * 0.42 && node.ny > 0.57 && target.ny > 0.57;
  }

  if (regions.has("face") && regions.has("neck")) {
    return distance < connectionDistance * 0.32 && node.ny < 0.57 && target.ny < 0.57;
  }

  if (regions.has("cap") && regions.has("face")) {
    return distance < connectionDistance * 0.45 && node.ny < 0.42 && target.ny < 0.42;
  }

  return false;
}
