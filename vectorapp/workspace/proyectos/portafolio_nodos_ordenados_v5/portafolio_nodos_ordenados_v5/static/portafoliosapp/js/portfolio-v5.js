(() => {
  "use strict";

  const modules = Array.isArray(window.BUBBLES) ? window.BUBBLES : [];
  const meta = window.PORTFOLIO_META || {};
  const graphStage = document.getElementById("graph-stage");
  const graphLines = document.getElementById("graph-lines");
  const graphWrap = document.getElementById("graph-wrap");
  const rail = document.getElementById("node-rail");
  const stack = document.getElementById("module-stack");
  const explorer = document.getElementById("explorar");
  const header = document.getElementById("site-header");
  const mediaDialog = document.getElementById("media-dialog");
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const colorFallback = ["#7cf29a", "#8ee5a6", "#78dce8", "#f5b971", "#a9e6bd", "#f0c681", "#b8e986"];
  let morphPlayed = false;
  let resizeTimer = 0;
  let zoom = { scale: 1, x: 0, y: 0, dragging: false, startX: 0, startY: 0, originX: 0, originY: 0 };

  if (!modules.length || !graphStage || !rail || !stack) return;

  const esc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  const accent = (module, index = 0) => module.color || colorFallback[index % colorFallback.length];
  const icon = (name) => `<i class="bi ${esc(name || "bi-circle")}" aria-hidden="true"></i>`;
  const moduleById = (id) => modules.find((item) => item.id === id);

  function renderGraph() {
    graphStage.innerHTML = "";
    graphLines.innerHTML = "";
    const centerIndex = Math.max(0, modules.findIndex((item) => item.type === "center"));
    const center = modules[centerIndex];
    const orbitModules = modules.filter((_, index) => index !== centerIndex);

    const centerButton = createGraphNode(center, centerIndex, true);
    graphStage.appendChild(centerButton);
    centerButton.dataset.x = "50";
    centerButton.dataset.y = "50";

    const mobile = window.innerWidth <= 620;
    const radiusX = mobile ? 39 : 40;
    const radiusY = mobile ? 35 : 38;
    const startAngle = -Math.PI / 2;
    orbitModules.forEach((item, orbitIndex) => {
      const sourceIndex = modules.indexOf(item);
      const angle = startAngle + (Math.PI * 2 * orbitIndex) / orbitModules.length;
      const x = 50 + Math.cos(angle) * radiusX;
      const y = 50 + Math.sin(angle) * radiusY;
      const button = createGraphNode(item, sourceIndex, false);
      button.dataset.x = String(x);
      button.dataset.y = String(y);
      graphStage.appendChild(button);
    });
    positionGraphNodes();
    requestAnimationFrame(drawGraphLines);
  }

  function createGraphNode(item, index, isCenter) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `graph-node${isCenter ? " is-center" : ""}`;
    button.dataset.moduleId = item.id;
    button.style.setProperty("--node-accent", accent(item, index));
    button.innerHTML = `${icon(item.icon)}<span>${esc(item.label)}</span>${isCenter ? `<small>${esc(meta.name || "")}</small>` : ""}`;
    button.addEventListener("click", () => openModule(item.id, { scroll: true, open: true }));
    return button;
  }

  function positionGraphNodes() {
    graphStage.querySelectorAll(".graph-node").forEach((node) => {
      node.style.left = `${node.dataset.x}%`;
      node.style.top = `${node.dataset.y}%`;
    });
  }

  function drawGraphLines() {
    const wrapRect = graphWrap.getBoundingClientRect();
    const center = graphStage.querySelector(".graph-node.is-center");
    if (!center) return;
    const cRect = center.getBoundingClientRect();
    const cx = cRect.left + cRect.width / 2 - wrapRect.left;
    const cy = cRect.top + cRect.height / 2 - wrapRect.top;
    graphLines.setAttribute("viewBox", `0 0 ${wrapRect.width} ${wrapRect.height}`);
    graphLines.innerHTML = "";
    graphStage.querySelectorAll(".graph-node:not(.is-center)").forEach((node, index) => {
      const rect = node.getBoundingClientRect();
      const x = rect.left + rect.width / 2 - wrapRect.left;
      const y = rect.top + rect.height / 2 - wrapRect.top;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", cx); line.setAttribute("y1", cy); line.setAttribute("x2", x); line.setAttribute("y2", y);
      if (index < 2) line.classList.add("is-primary");
      graphLines.appendChild(line);
    });
  }

  function renderExplorer() {
    rail.innerHTML = "";
    stack.innerHTML = "";
    modules.forEach((item, index) => {
      rail.appendChild(createRailNode(item, index));
      stack.appendChild(createModuleCard(item, index));
    });

    // Un reclutador ve valor inmediatamente, pero puede cerrar o abrir cualquier módulo.
    setModuleOpen("projects", true, false);
    setModuleOpen("profile", true, false);
    syncRailState();
  }

  function createRailNode(item, index) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rail-node";
    button.dataset.railId = item.id;
    button.style.setProperty("--node-accent", accent(item, index));
    button.innerHTML = `<span class="rail-node-dot">${icon(item.icon)}</span><span class="rail-node-label">${esc(item.label)}</span><span class="rail-node-state"><i class="bi bi-plus-lg"></i></span>`;
    button.addEventListener("click", () => {
      const card = stack.querySelector(`[data-module-card="${CSS.escape(item.id)}"]`);
      const willOpen = card ? !card.open : true;
      setModuleOpen(item.id, willOpen, true);
    });
    return button;
  }

  function createModuleCard(item, index) {
    const card = document.createElement("details");
    card.className = "module-card";
    card.dataset.moduleCard = item.id;
    card.style.setProperty("--module-accent", accent(item, index));
    const summary = document.createElement("summary");
    summary.className = "module-summary";
    summary.innerHTML = `
      <span class="module-number">${String(index + 1).padStart(2, "0")}</span>
      <span class="module-title-group">
        <span class="module-title-row">${icon(item.icon)}<h3>${esc(item.label)}</h3></span>
        <p>${esc(item.content || item.text || "")}</p>
      </span>
      <span class="module-toggle" aria-hidden="true"><i class="bi bi-plus-lg"></i></span>`;
    const content = document.createElement("div");
    content.className = "module-content";
    content.innerHTML = `<div class="module-content-inner">${renderModule(item, index)}</div>`;
    card.append(summary, content);
    card.addEventListener("toggle", () => {
      syncRailState();
      if (card.open && !prefersReduced && window.anime) {
        const target = card.querySelector(".module-content-inner");
        anime.remove(target);
        anime({targets: target, opacity:[0,1], translateY:[10,0], duration:320, easing:"easeOutCubic"});
      }
    });
    return card;
  }

  function renderModule(item, index) {
    if (item.id === "profile") return renderProfile(item);
    if (item.id === "projects") return renderProjects(item);
    if (item.id === "experience") return renderExperience(item);
    if (item.id === "education") return renderEducation(item);
    if (item.id === "contact") return renderContact(item);
    return renderGenericModule(item, index);
  }

  function renderProfile(item) {
    return `
      <div class="content-lead">
        <div>
          <h4>${esc(item.name || meta.name || item.label)}</h4>
          <p>${esc(item.tagline || "")}</p>
          <p style="margin-top:12px">${esc(item.content || "")}</p>
          ${renderActions(item.actions)}
        </div>
        ${renderTags(item.stats || [])}
      </div>
      ${renderSections(item.sections)}
    `;
  }

  function renderProjects(item) {
    const cases = item.children || [];
    if (!cases.length) return renderGenericModule(item);
    return cases.map((project) => renderCase(project)).join("");
  }

  function renderCase(project) {
    const minuta = project.minuta || {};
    const sections = project.sections || [];
    return `
      <article class="case-study">
        <div class="case-hero">
          <div>
            <span class="case-badge">${esc(project.badge || "Proyecto")}</span>
            <h4 class="case-title">${esc(project.label)}</h4>
            <p class="case-copy">${esc(project.content || project.text || "")}</p>
            ${renderTags(project.tags || [])}
          </div>
          ${minuta.outcome ? `<aside class="outcome-card"><span>Impacto</span><strong>${esc(minuta.outcome)}</strong></aside>` : ""}
        </div>
        ${renderArchitecture(project.architecture)}
        ${renderSections(sections)}
        ${project.note ? `<p class="case-note"><i class="bi bi-shield-lock"></i> ${esc(project.note)}</p>` : ""}
        ${renderSimulation(project.simulation)}
      </article>
    `;
  }

  function renderArchitecture(items = []) {
    if (!items.length) return "";
    return `<div class="architecture"><div class="architecture-label">Arquitectura de solución</div><div class="architecture-flow">${items.map((item, index) => `${index ? '<i class="bi bi-arrow-right architecture-arrow"></i>' : ''}<span class="architecture-node">${esc(item)}</span>`).join("")}</div></div>`;
  }

  function renderSimulation(sim) {
    if (!sim || !Array.isArray(sim.steps)) return "";
    return `
      <section class="simulation">
        <div class="simulation-head"><div><h5>${esc(sim.title || "Flujo técnico")}</h5><p>${esc(sim.summary || "")}</p></div><span class="tag">${sim.steps.length} pasos</span></div>
        <div class="simulation-list">${sim.steps.map((step) => `<details class="sim-step"><summary>${icon(step.icon)}<strong>${esc(step.label)}</strong><span><i class="bi bi-plus-lg"></i></span></summary><p>${esc(step.detail || "")}</p></details>`).join("")}</div>
      </section>`;
  }

  function renderExperience(item) {
    const jobs = item.children || [];
    return `
      <div class="content-lead"><div><h4>Experiencia aplicada a operación real</h4><p>${esc(item.content || "")}</p></div>${renderTags(jobs.flatMap((j) => j.tags || []))}</div>
      <div class="child-grid">${jobs.map((job) => renderChild(job, { open: true, includeRelated: true })).join("")}</div>`;
  }

  function renderEducation(item) {
    const children = item.children || [];
    const location = children.find((child) => child.kind === "location");
    const credentials = children.filter((child) => child.kind !== "location");
    return `
      <div class="content-lead"><div><h4>Formación y evidencia verificable</h4><p>${esc(item.content || "")}</p></div>${item.institution ? renderTags([item.institution]) : ""}</div>
      ${location ? renderLocation(location) : ""}
      <div style="height:10px"></div>
      <div class="child-grid">${credentials.map((credential) => renderChild(credential)).join("")}</div>`;
  }

  function renderLocation(data) {
    return `<article class="location-card">
      ${data.map_embed ? `<iframe loading="lazy" src="${esc(data.map_embed)}" title="Mapa de ${esc(data.label)}"></iframe>` : ""}
      <div class="location-copy"><strong>${esc(data.label)}</strong><p>${esc(data.text || data.map_address || "")}</p><div class="action-row">
        ${data.map_link ? `<a class="content-action" href="${esc(data.map_link)}" target="_blank" rel="noopener"><i class="bi bi-map"></i> Ver en Maps</a>` : ""}
        ${data.route ? `<button class="content-action" type="button" data-route data-destination="${esc(data.route_destination || "")}"><i class="bi bi-sign-turn-right"></i> Ruta desde mi ubicación</button>` : ""}
      </div></div></article>`;
  }

  function renderContact(item) {
    return `
      <div class="content-lead"><div><h4>Conversemos</h4><p>${esc(item.content || "")}</p></div></div>
      <div class="contact-grid">${(item.children || []).map((child) => renderContactCard(child)).join("")}</div>`;
  }

  function renderContactCard(child) {
    const isExternal = child.href && child.href !== "#" && !child.secret_kind?.match(/email|phone/);
    const action = isExternal
      ? `<a class="contact-go" href="${esc(child.href)}" target="_blank" rel="noopener" aria-label="Abrir ${esc(child.label)}"><i class="bi bi-arrow-up-right"></i></a>`
      : child.secret_value
        ? `<button type="button" data-reveal-contact data-token="${esc(child.secret_value)}" data-kind="${esc(child.secret_kind || "")}" aria-label="Revelar ${esc(child.label)}"><i class="bi bi-eye"></i></button>`
        : "";
    return `<article class="contact-card"><span class="contact-icon">${icon(child.icon)}</span><div class="contact-copy"><strong>${esc(child.label)}</strong><span data-contact-value>${esc(child.text || "")}</span></div>${action}</article>`;
  }

  function renderGenericModule(item) {
    const children = item.children || [];
    return `
      <div class="content-lead"><div><h4>${esc(item.label)}</h4><p>${esc(item.content || item.text || "")}</p></div>${renderTags(item.stats || item.tags || [])}</div>
      ${item.sections ? renderSections(item.sections) : ""}
      ${children.length ? `<div class="child-grid">${children.map((child) => renderChild(child)).join("")}</div>` : ""}`;
  }

  function renderChild(child, options = {}) {
    const evidence = child.evidence ? renderEvidence(child.evidence, child.label) : "";
    const gallery = Array.isArray(child.gallery) ? child.gallery.map((img) => renderEvidence(img, child.label)).join("") : "";
    const metaBits = [child.badge, child.level, child.issuer, child.date].filter(Boolean);
    const related = options.includeRelated && child.related_project ? `<div class="action-row"><button type="button" class="content-action" data-open-module="projects"><i class="bi bi-box-seam"></i> Ver proyecto relacionado</button></div>` : "";
    return `<details class="child-card" ${options.open ? "open" : ""}>
      <summary class="child-summary"><span class="child-icon">${icon(child.icon)}</span><span class="child-title"><strong>${esc(child.label)}</strong><small>${esc(metaBits.slice(0,2).join(" · ") || child.kind || "Detalle")}</small></span><span class="child-plus"><i class="bi bi-plus-lg"></i></span></summary>
      <div class="child-body">
        ${metaBits.length ? `<div class="credential-meta">${metaBits.map((m) => `<span class="meta-chip">${esc(m)}</span>`).join("")}</div>` : ""}
        <p>${esc(child.text || child.content || "")}</p>
        ${child.sections ? renderSections(child.sections) : ""}
        ${renderTags(child.tags || [])}
        ${evidence}${gallery}${related}
      </div>
    </details>`;
  }

  function renderSections(sections = []) {
    if (!Array.isArray(sections) || !sections.length) return "";
    return `<div class="info-grid">${sections.map((section) => `<article class="info-block">${icon(section.icon)}<h5>${esc(section.heading || "Detalle")}</h5>${Array.isArray(section.items) ? `<ul>${section.items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}</article>`).join("")}</div>`;
  }

  function renderTags(tags = []) {
    const unique = [...new Set((tags || []).filter(Boolean))].slice(0, 18);
    return unique.length ? `<div class="tag-cloud">${unique.map((tag) => `<span class="tag">${esc(tag)}</span>`).join("")}</div>` : "";
  }

  function renderActions(actions = []) {
    if (!Array.isArray(actions) || !actions.length) return "";
    return `<div class="action-row">${actions.map((action) => `<a class="content-action" href="${esc(action.href || "#")}">${icon(action.icon)} ${esc(action.label)}</a>`).join("")}</div>`;
  }

  function renderEvidence(image, label) {
    if (!image || !image.src) return "";
    return `<button type="button" class="evidence-button" data-media-src="${esc(image.src)}" data-media-alt="${esc(image.alt || label || "Evidencia")}" data-media-caption="${esc(image.caption || image.alt || label || "Evidencia")}"><img class="evidence-thumb" loading="lazy" src="${esc(image.src)}" alt="${esc(image.alt || label || "Evidencia")}"><span>${esc(image.caption || "Ver evidencia")} <i class="bi bi-arrows-angle-expand"></i></span></button>`;
  }

  function setModuleOpen(id, open, shouldScroll = false) {
    const card = stack.querySelector(`[data-module-card="${CSS.escape(id)}"]`);
    if (!card) return;
    card.open = Boolean(open);
    if (shouldScroll) card.scrollIntoView({behavior: prefersReduced ? "auto" : "smooth", block:"start"});
    syncRailState();
  }

  function openModule(id, { scroll = true, open = true } = {}) {
    if (scroll) explorer.scrollIntoView({behavior: prefersReduced ? "auto" : "smooth", block:"start"});
    window.setTimeout(() => setModuleOpen(id, open, true), prefersReduced ? 0 : 420);
  }

  function syncRailState() {
    modules.forEach((item) => {
      const card = stack.querySelector(`[data-module-card="${CSS.escape(item.id)}"]`);
      const button = rail.querySelector(`[data-rail-id="${CSS.escape(item.id)}"]`);
      if (!card || !button) return;
      button.classList.toggle("is-active", card.open);
      const state = button.querySelector(".rail-node-state i");
      if (state) state.className = `bi ${card.open ? "bi-dash-lg" : "bi-plus-lg"}`;
      button.setAttribute("aria-expanded", card.open ? "true" : "false");
    });
  }

  function morphHeroNodesToRail() {
    if (morphPlayed || prefersReduced) return;
    morphPlayed = true;
    const heroNodes = [...graphStage.querySelectorAll(".graph-node")];
    heroNodes.forEach((source, index) => {
      const id = source.dataset.moduleId;
      const target = rail.querySelector(`[data-rail-id="${CSS.escape(id)}"] .rail-node-dot`);
      if (!target) return;
      const a = source.getBoundingClientRect();
      const b = target.getBoundingClientRect();
      if (a.bottom < 0 || b.top > window.innerHeight * 1.5) return;
      const clone = source.cloneNode(true);
      clone.classList.add("morph-clone");
      Object.assign(clone.style, {left:`${a.left}px`, top:`${a.top}px`, width:`${a.width}px`, height:`${a.height}px`, minHeight:`${a.height}px`});
      document.body.appendChild(clone);
      const dx = b.left - a.left;
      const dy = b.top - a.top;
      anime({targets:clone, translateX:dx, translateY:dy, width:[a.width,b.width], height:[a.height,b.height], borderRadius:[parseFloat(getComputedStyle(source).borderRadius) || 20, 13], opacity:[1,.15], scale:[1,.72], delay:index*35, duration:620, easing:"easeInOutCubic", complete:()=>clone.remove()});
    });
  }


  function updateScrollMorph() {
    if (window.innerWidth <= 880) {
      graphStage.querySelectorAll(".graph-node").forEach((node) => {
        node.style.left = `${node.dataset.x}%`;
        node.style.top = `${node.dataset.y}%`;
        node.style.transform = "translate(-50%, -50%) scale(1)";
        node.style.opacity = "1";
      });
      if (graphLines) graphLines.style.opacity = "1";
      return;
    }
    const hero = document.getElementById("inicio");
    if (!hero) return;
    const maxTravel = Math.max(1, hero.offsetHeight - window.innerHeight);
    const raw = Math.max(0, Math.min(1, (window.scrollY - hero.offsetTop) / maxTravel));
    const p = Math.max(0, Math.min(1, (raw - 0.10) / 0.78));
    const eased = p * p * (3 - 2 * p);
    const nodes = [...graphStage.querySelectorAll(".graph-node")];
    nodes.forEach((node, index) => {
      const sx = Number(node.dataset.x || 50);
      const sy = Number(node.dataset.y || 50);
      const tx = 14;
      const ty = 13 + index * (74 / Math.max(1, nodes.length - 1));
      const x = sx + (tx - sx) * eased;
      const y = sy + (ty - sy) * eased;
      node.style.left = `${x}%`;
      node.style.top = `${y}%`;
      node.style.transform = `translate(-50%, -50%) scale(${1 - eased * 0.20})`;
      node.style.opacity = `${1 - eased * 0.08}`;
    });
    if (graphLines) {
      graphLines.style.opacity = String(1 - eased * 0.92);
      if (eased < 0.96) drawGraphLines();
    }
    const label = graphWrap?.querySelector(".graph-label");
    if (label) label.style.opacity = String(1 - eased);
  }

  function observeExplorer() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) morphPlayed = true;
      });
    }, { threshold: 0.05, rootMargin:"0px 0px 18% 0px" });
    observer.observe(explorer);

    const cardObserver = new IntersectionObserver((entries) => {
      entries.filter((entry) => entry.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio).slice(0,1).forEach((entry) => {
        const id = entry.target.dataset.moduleCard;
        rail.querySelectorAll(".rail-node").forEach((node) => node.classList.toggle("is-current", node.dataset.railId === id));
      });
    }, {threshold:[.2,.45,.7], rootMargin:"-20% 0px -55% 0px"});
    stack.querySelectorAll(".module-card").forEach((card) => cardObserver.observe(card));
  }

  async function revealContact(button) {
    const token = button.dataset.token;
    if (!token) return;
    const card = button.closest(".contact-card");
    const value = card?.querySelector("[data-contact-value]");
    const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
    button.disabled = true;
    try {
      const response = await fetch("/api/reveal-contact/", {method:"POST", headers:{"Content-Type":"application/json","X-CSRFToken":csrf}, body:JSON.stringify({token})});
      if (!response.ok) throw new Error("No se pudo revelar");
      const data = await response.json();
      if (value) value.textContent = data.value;
      const kind = button.dataset.kind;
      if (kind === "email") button.outerHTML = `<a class="contact-go" href="mailto:${esc(data.value)}" aria-label="Enviar correo"><i class="bi bi-envelope-arrow-up"></i></a>`;
      else if (kind === "phone") button.outerHTML = `<a class="contact-go" href="tel:${esc(data.value.replace(/\s+/g,""))}" aria-label="Llamar"><i class="bi bi-telephone-outbound"></i></a>`;
      else button.innerHTML = '<i class="bi bi-check2"></i>';
    } catch (_) {
      if (value) value.textContent = "No fue posible revelar este dato.";
      button.disabled = false;
    }
  }

  function requestRoute(button) {
    const destination = button.dataset.destination;
    if (!destination) return;
    if (!navigator.geolocation) {
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}&travelmode=driving`, "_blank", "noopener");
      return;
    }
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="bi bi-geo"></i> Solicitando ubicación…';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const origin = `${pos.coords.latitude},${pos.coords.longitude}`;
        window.open(`https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&travelmode=driving`, "_blank", "noopener");
        button.disabled = false; button.innerHTML = original;
      },
      () => {
        window.open(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}&travelmode=driving`, "_blank", "noopener");
        button.disabled = false; button.innerHTML = original;
      },
      {enableHighAccuracy:false, timeout:7000, maximumAge:300000}
    );
  }

  function openMedia(button) {
    if (!mediaDialog) return;
    const img = mediaDialog.querySelector("[data-media-image]");
    const cap = mediaDialog.querySelector("[data-media-caption]");
    img.src = button.dataset.mediaSrc || "";
    img.alt = button.dataset.mediaAlt || "Evidencia";
    cap.textContent = button.dataset.mediaCaption || "";
    resetZoom();
    mediaDialog.showModal();
  }

  function applyZoom() {
    const img = mediaDialog?.querySelector("[data-media-image]");
    const label = mediaDialog?.querySelector("[data-zoom-label]");
    if (!img) return;
    img.style.transform = `translate3d(${zoom.x}px,${zoom.y}px,0) scale(${zoom.scale})`;
    if (label) label.textContent = `${Math.round(zoom.scale*100)}%`;
  }
  function setZoom(next) { zoom.scale = Math.max(1, Math.min(4, next)); if (zoom.scale===1){zoom.x=0;zoom.y=0;} applyZoom(); }
  function resetZoom(){ zoom={scale:1,x:0,y:0,dragging:false,startX:0,startY:0,originX:0,originY:0}; applyZoom(); }

  document.addEventListener("click", (event) => {
    const reveal = event.target.closest("[data-reveal-contact]");
    if (reveal) { revealContact(reveal); return; }
    const route = event.target.closest("[data-route]");
    if (route) { requestRoute(route); return; }
    const media = event.target.closest("[data-media-src]");
    if (media) { openMedia(media); return; }
    const open = event.target.closest("[data-open-module]");
    if (open) { openModule(open.dataset.openModule, {scroll:true,open:true}); return; }
  });

  document.querySelector("[data-expand-all]")?.addEventListener("click", () => {
    stack.querySelectorAll(".module-card").forEach((card) => card.open = true);
    syncRailState();
  });
  document.querySelector("[data-collapse-all]")?.addEventListener("click", () => {
    stack.querySelectorAll(".module-card").forEach((card) => card.open = false);
    syncRailState();
  });

  document.querySelector("[data-dialog-close]")?.addEventListener("click", () => mediaDialog?.close());
  mediaDialog?.addEventListener("click", (event) => { if (event.target === mediaDialog) mediaDialog.close(); });
  mediaDialog?.querySelectorAll("[data-zoom]").forEach((button) => button.addEventListener("click", () => {
    const action = button.dataset.zoom;
    if (action === "in") setZoom(zoom.scale + .35);
    if (action === "out") setZoom(zoom.scale - .35);
    if (action === "reset") resetZoom();
  }));
  const viewport = mediaDialog?.querySelector("[data-media-viewport]");
  viewport?.addEventListener("wheel", (event) => { event.preventDefault(); setZoom(zoom.scale + (event.deltaY < 0 ? .2 : -.2)); }, {passive:false});
  viewport?.addEventListener("pointerdown", (event) => { if (zoom.scale <= 1) return; zoom.dragging=true; zoom.startX=event.clientX;zoom.startY=event.clientY;zoom.originX=zoom.x;zoom.originY=zoom.y;viewport.classList.add("is-dragging");viewport.setPointerCapture(event.pointerId); });
  viewport?.addEventListener("pointermove", (event) => { if(!zoom.dragging)return;zoom.x=zoom.originX+event.clientX-zoom.startX;zoom.y=zoom.originY+event.clientY-zoom.startY;applyZoom(); });
  viewport?.addEventListener("pointerup", (event) => { zoom.dragging=false;viewport.classList.remove("is-dragging"); if(viewport.hasPointerCapture(event.pointerId))viewport.releasePointerCapture(event.pointerId); });

  window.addEventListener("scroll", () => { header?.classList.toggle("is-scrolled", window.scrollY > 18); updateScrollMorph(); }, {passive:true});
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer=setTimeout(()=>{renderGraph(); updateScrollMorph();},140); }, {passive:true});

  renderGraph();
  renderExplorer();
  observeExplorer();
  updateScrollMorph();
})();
