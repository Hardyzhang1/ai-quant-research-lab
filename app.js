const canvas = document.getElementById("field");
const ctx = canvas.getContext("2d");

let width = 0;
let height = 0;
let points = [];
let pointer = { x: 0, y: 0, active: false };

function resize() {
  const dpr = window.devicePixelRatio || 1;
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const count = Math.min(120, Math.max(54, Math.floor((width * height) / 15000)));
  points = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.32,
    vy: (Math.random() - 0.5) * 0.32,
    r: 1 + Math.random() * 1.8,
  }));
}

function draw() {
  ctx.clearRect(0, 0, width, height);

  for (const p of points) {
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < -20) p.x = width + 20;
    if (p.x > width + 20) p.x = -20;
    if (p.y < -20) p.y = height + 20;
    if (p.y > height + 20) p.y = -20;
  }

  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      const a = points[i];
      const b = points[j];
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 132) {
        const alpha = (1 - dist / 132) * 0.22;
        ctx.strokeStyle = `rgba(106, 231, 255, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
  }

  if (pointer.active) {
    for (const p of points) {
      const dx = p.x - pointer.x;
      const dy = p.y - pointer.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 180) {
        ctx.strokeStyle = `rgba(99, 245, 178, ${(1 - dist / 180) * 0.28})`;
        ctx.beginPath();
        ctx.moveTo(pointer.x, pointer.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
      }
    }
  }

  for (const p of points) {
    ctx.fillStyle = "rgba(238, 243, 255, 0.72)";
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
  }

  requestAnimationFrame(draw);
}

window.addEventListener("resize", resize);
window.addEventListener("pointermove", (event) => {
  pointer = { x: event.clientX, y: event.clientY, active: true };
});
window.addEventListener("pointerleave", () => {
  pointer.active = false;
});

resize();
draw();

function pct(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function tone(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "";
  return value >= 0 ? "positive" : "negative";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function periodBlock(label, data, field) {
  const value = data ? data[field] : null;
  return `
    <div class="period-cell">
      <span>${label} ${field === "long" ? "long" : "long-short"}</span>
      <strong class="${tone(value)}">${pct(value)}</strong>
    </div>
  `;
}

async function loadSnapshot() {
  const grid = document.getElementById("snapshotGrid");
  const meta = document.getElementById("snapshotMeta");
  if (!grid || !meta) return;
  try {
    const response = await fetch("data/top3-performance.json", { cache: "no-store" });
    if (!response.ok) throw new Error("No snapshot published yet");
    const snapshot = await response.json();
    const rows = snapshot.top || [];
    meta.textContent = `Published ${snapshot.published_at || snapshot.collected_at || "recently"} | Latest source date ${rows[0]?.latest_date || "--"} | Manual snapshot`;
    grid.innerHTML = rows.map((row, index) => {
      const p = row.periods || {};
      return `
        <article class="snapshot-card">
          <h3>Factor ${index + 1}</h3>
          <div class="snapshot-date">Latest: ${row.latest_date || "--"}</div>
          <div class="period-grid">
            ${periodBlock("1D", p["1D"], "long")}
            ${periodBlock("1D", p["1D"], "long_short")}
            ${periodBlock("7D", p["7D"], "long")}
            ${periodBlock("7D", p["7D"], "long_short")}
            ${periodBlock("1M", p["1M"], "long")}
            ${periodBlock("1M", p["1M"], "long_short")}
            ${periodBlock("Jul 1+", p.since_2026_07_01, "long")}
            ${periodBlock("Jul 1+", p.since_2026_07_01, "long_short")}
          </div>
        </article>
      `;
    }).join("");
  } catch (error) {
    meta.textContent = "No public snapshot has been published yet.";
    grid.innerHTML = "";
  }
}

loadSnapshot();

function briefCard(brief) {
  const tags = Array.isArray(brief.tags) ? brief.tags : [];
  const bullets = Array.isArray(brief.bullets) ? brief.bullets : [];
  const stats = Array.isArray(brief.stats) ? brief.stats : [];
  const items = Array.isArray(brief.items) ? brief.items : [];
  const recommendations = Array.isArray(brief.recommendations) ? brief.recommendations : [];
  const updated = brief.updated_at || "--";
  return `
    <article class="brief-card">
      <div class="brief-topline">
        <span>${escapeHtml(brief.market || "Agent")}</span>
        <span>${escapeHtml(updated)}</span>
      </div>
      <h3>${escapeHtml(brief.title || "Sanitized agent brief")}</h3>
      <p>${escapeHtml(brief.summary || "A public-safe snapshot will appear here after the next refresh.")}</p>
      <div class="brief-pill-row">
        ${tags.map((tag) => `<span class="brief-pill">${escapeHtml(tag)}</span>`).join("")}
      </div>
      ${stats.length ? `
        <div class="brief-stat-grid">
          ${stats.slice(0, 4).map((stat) => `
            <div class="brief-stat">
              <span>${escapeHtml(stat.label)}</span>
              <strong>${escapeHtml(stat.value)}</strong>
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${items.length ? `
        <div class="brief-section-title">Latest public news digest</div>
        <div class="brief-item-list">
          ${items.slice(0, 8).map((item) => `
            <div class="brief-item">
              <div class="brief-item-top">
                <span>${escapeHtml(item.market || "news")}</span>
                <span>${escapeHtml(item.tone || "--")}</span>
              </div>
              <strong>${escapeHtml(item.title || "Untitled item")}</strong>
              <p>${escapeHtml(item.summary || "")}</p>
              ${item.related ? `<div class="brief-related">${escapeHtml(item.related)}</div>` : ""}
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${recommendations.length ? `
        <div class="brief-section-title">Latest public research signals</div>
        <div class="brief-item-list">
          ${recommendations.slice(0, 5).map((item) => `
            <div class="brief-item recommendation-item">
              <div class="brief-item-top">
                <span>${escapeHtml(item.status || "research state")}</span>
                <span>${escapeHtml(item.horizon || "--")}</span>
              </div>
              <strong>${escapeHtml(item.title || "Research item")}</strong>
              ${(item.symbol || item.name) ? `<div class="brief-symbol">${escapeHtml([item.symbol, item.name].filter(Boolean).join(" | "))}</div>` : ""}
              <p>${escapeHtml(item.summary || "")}</p>
              <div class="brief-related">${escapeHtml(item.industry || "")}${item.reason ? ` · ${escapeHtml(item.reason)}` : ""}</div>
              ${Array.isArray(item.metrics) && item.metrics.length ? `
                <div class="brief-metric-row">
                  ${item.metrics.slice(0, 4).map((metric) => `
                    <span>${escapeHtml(metric.label)}: ${escapeHtml(metric.value)}</span>
                  `).join("")}
                </div>
              ` : ""}
            </div>
          `).join("")}
        </div>
      ` : ""}
      <ul class="brief-list">
        ${bullets.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
      <div class="brief-disclaimer">
        Public display only. Not investment advice. Core models, prompts, data sources,
        trading logic, infrastructure details, and execution rules are intentionally withheld.
      </div>
    </article>
  `;
}

function renderBriefPulse(payload, briefs) {
  const pulse = document.getElementById("briefPulse");
  if (!pulse) return;
  const guardCount = new Set(
    briefs.flatMap((brief) => Array.isArray(brief.tags) ? brief.tags : [])
  ).size;
  const surfaces = briefs.length;
  const updated = payload.published_at || "pending";
  const scope = payload.scope || "sanitized_public_showcase";
  pulse.innerHTML = `
    <div class="pulse-item">
      <span>Surfaces</span>
      <strong>${surfaces}</strong>
    </div>
    <div class="pulse-item">
      <span>Privacy Guards</span>
      <strong>${guardCount}</strong>
    </div>
    <div class="pulse-item">
      <span>Refresh</span>
      <strong>Manual</strong>
    </div>
    <div class="pulse-item wide">
      <span>Scope</span>
      <strong>${escapeHtml(scope.replaceAll("_", " "))}</strong>
    </div>
    <div class="pulse-item wide">
      <span>Updated</span>
      <strong>${escapeHtml(updated)}</strong>
    </div>
  `;
}

function emailTable(table) {
  const headers = Array.isArray(table.headers) ? table.headers : [];
  const rows = Array.isArray(table.rows) ? table.rows : [];
  if (!headers.length && !rows.length) return "";
  return `
    <div class="email-table-wrap">
      <table class="email-table">
        ${headers.length ? `
          <thead>
            <tr>${headers.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("")}</tr>
          </thead>
        ` : ""}
        <tbody>
          ${rows.map((row) => `
            <tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function emailMirrorCard(email) {
  const lines = Array.isArray(email.lines) ? email.lines : [];
  const tables = Array.isArray(email.tables) ? email.tables : [];
  return `
    <article class="email-card">
      <div class="brief-topline">
        <span>${escapeHtml(email.source || "public mirror")}</span>
        <span>${escapeHtml(email.updated_at || "--")}</span>
      </div>
      <h3>${escapeHtml(email.title || "Published email")}</h3>
      <div class="email-line-list">
        ${lines.slice(0, 90).map((line) => `<p>${escapeHtml(line)}</p>`).join("")}
      </div>
      ${tables.length ? `
        <div class="brief-section-title">Mirrored tables</div>
        ${tables.slice(0, 6).map(emailTable).join("")}
      ` : ""}
      <div class="brief-disclaimer">
        Mirrored after email delivery. Private recipients, secrets, local paths,
        infrastructure details, source links, and implementation internals are redacted.
      </div>
    </article>
  `;
}

function renderEmailMirrors(payload) {
  const grid = document.getElementById("emailMirrorGrid");
  const meta = document.getElementById("emailMirrorMeta");
  if (!grid || !meta) return;
  const emails = Array.isArray(payload.email_mirrors) ? payload.email_mirrors : [];
  meta.textContent = emails.length
    ? `Published ${payload.published_at || "recently"} | ${emails.length} mirrored email surfaces`
    : "No mirrored email content has been published yet. Pass private email preview paths to the refresh script.";
  grid.innerHTML = emails.length ? emails.map(emailMirrorCard).join("") : "";
}

async function loadAgentBriefs() {
  const grid = document.getElementById("briefGrid");
  const meta = document.getElementById("briefMeta");
  if (!grid || !meta) return;
  try {
    const response = await fetch("data/agent-briefs.json", { cache: "no-store" });
    if (!response.ok) throw new Error("No agent brief snapshot published yet");
    const payload = await response.json();
    const briefs = Array.isArray(payload.briefs) ? payload.briefs : [];
    renderBriefPulse(payload, briefs);
    renderEmailMirrors(payload);
    meta.textContent = `Published ${payload.published_at || "recently"} | ${briefs.length} sanitized surfaces | Private implementation withheld`;
    grid.innerHTML = briefs.length
      ? briefs.map(briefCard).join("")
      : "";
  } catch (error) {
    renderBriefPulse({ published_at: "waiting", scope: "no_public_snapshot" }, []);
    renderEmailMirrors({ email_mirrors: [] });
    meta.textContent = "No public agent brief snapshot has been published yet.";
    grid.innerHTML = "";
  }
}

loadAgentBriefs();
