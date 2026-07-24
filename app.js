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

function metricBlock(label, value, suffix = "") {
  return `
    <div class="period-cell">
      <span>${label}</span>
      <strong class="${tone(value)}">${suffix === "ratio" ? ratio(value) : pct(value)}</strong>
    </div>
  `;
}

function metricValue(label, value) {
  return `
    <div class="period-cell">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value ?? "--")}</strong>
    </div>
  `;
}

function ratio(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return value.toFixed(2);
}

function groupReturnSvg(series) {
  const rows = Array.isArray(series) ? series.filter((s) => Array.isArray(s.data) && s.data.length) : [];
  if (!rows.length) return `<div class="snapshot-empty-chart">No group-return chart yet</div>`;
  const widthSvg = 640;
  const heightSvg = 210;
  const pad = { left: 46, right: 18, top: 18, bottom: 34 };
  const values = rows.flatMap((row) => row.data.map((point) => Number(point[1])).filter(Number.isFinite));
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min || 1;
  const colors = ["#ff6b8b", "#ffc857", "#40d9ff", "#63f5b2", "#b9f"];
  const xFor = (i, n) => pad.left + (n <= 1 ? 0 : (i / (n - 1)) * (widthSvg - pad.left - pad.right));
  const yFor = (v) => pad.top + (1 - ((v - min) / span)) * (heightSvg - pad.top - pad.bottom);
  const zeroY = yFor(0);
  const lines = rows.map((row, rowIndex) => {
    const points = row.data.map((point, i) => `${xFor(i, row.data.length).toFixed(1)},${yFor(Number(point[1])).toFixed(1)}`).join(" ");
    return `<polyline points="${points}" fill="none" stroke="${colors[rowIndex % colors.length]}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />`;
  }).join("");
  const firstDate = rows[0].data[0]?.[0] || "";
  const lastDate = rows[0].data.at(-1)?.[0] || "";
  const legend = rows.map((row, i) => `
    <span><i style="background:${colors[i % colors.length]}"></i>${escapeHtml(row.name || `Q${i + 1}`)}</span>
  `).join("");
  return `
    <div class="snapshot-chart-wrap">
      <svg class="snapshot-chart" viewBox="0 0 ${widthSvg} ${heightSvg}" role="img" aria-label="Group return time series">
        <line x1="${pad.left}" x2="${widthSvg - pad.right}" y1="${zeroY.toFixed(1)}" y2="${zeroY.toFixed(1)}" class="chart-zero" />
        <text x="${pad.left}" y="${heightSvg - 12}" class="chart-axis">${escapeHtml(firstDate)}</text>
        <text x="${widthSvg - pad.right}" y="${heightSvg - 12}" text-anchor="end" class="chart-axis">${escapeHtml(lastDate)}</text>
        <text x="10" y="${yFor(max).toFixed(1)}" class="chart-axis">${pct(max)}</text>
        <text x="10" y="${yFor(min).toFixed(1)}" class="chart-axis">${pct(min)}</text>
        ${lines}
      </svg>
      <div class="snapshot-legend">${legend}</div>
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
    const strategies = Array.isArray(snapshot.strategies) ? snapshot.strategies : [];
    meta.textContent = `Published ${snapshot.published_at || snapshot.collected_at || "recently"} | Latest source date ${rows[0]?.latest_date || "--"} | Manual snapshot`;
    const factorCards = rows.map((row, index) => {
      const m = row.metrics || {};
      const chart = row.chart?.group_return || [];
      return `
        <article class="snapshot-card">
          <h3>Factor ${index + 1}</h3>
          <div class="snapshot-date">Latest: ${row.latest_date || "--"}</div>
          <div class="period-grid">
            ${metricBlock("Long annualized", m.long_ann)}
            ${metricBlock("Long excess annualized", m.long_excess_ann)}
            ${metricBlock("Long-short annualized", m.long_short_ann)}
            ${metricBlock("Factor Sharpe", m.factor_sharpe, "ratio")}
          </div>
          ${groupReturnSvg(chart)}
        </article>
      `;
    }).join("");
    const strategyCards = strategies.map((strategy) => {
      const m = strategy.metrics || {};
      const tracking = strategy.tracking || {};
      const benchmark = strategy.benchmark || {};
      return `
        <article class="snapshot-card strategy-snapshot-card">
          <h3>${escapeHtml(strategy.name || "Strategy")}</h3>
          <div class="snapshot-date">
            Tracking date: ${escapeHtml(tracking.latest_date || strategy.latest_date || "--")}
            ${benchmark.actual_start && benchmark.actual_end ? `<br>Tracked benchmark: CSI 300, ${escapeHtml(benchmark.actual_start)} to ${escapeHtml(benchmark.actual_end)}` : ""}
          </div>
          <div class="period-grid">
            ${metricBlock("Backtest annualized", m.annualized_return)}
            ${metricBlock("Backtest total return", m.total_return)}
            ${metricBlock("Max drawdown", m.max_drawdown)}
            ${metricBlock("Tracked since build", tracking.total_return)}
            ${typeof m.tracking_benchmark_total_return === "number" ? metricBlock("Tracked CSI 300", m.tracking_benchmark_total_return) : ""}
            ${typeof m.tracking_excess_total_return === "number" ? metricBlock("Tracked excess vs CSI 300", m.tracking_excess_total_return) : ""}
            ${metricBlock("Latest day reference", tracking.day_return)}
            ${metricValue("Sharpe", ratio(m.sharpe))}
          </div>
        </article>
      `;
    }).join("");
    grid.innerHTML = factorCards + strategyCards;
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

function reportTable(table) {
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

function reportSourceCard(report) {
  const highlights = Array.isArray(report.highlights) ? report.highlights : [];
  const tables = Array.isArray(report.tables) ? report.tables : [];
  return `
    <article class="report-source-card">
      <div class="brief-topline">
        <span>${escapeHtml(report.source || "agent report")}</span>
        <span>${escapeHtml(report.generated_at || report.updated_at || "--")}</span>
      </div>
      <h3>${escapeHtml(report.title || "Latest report")}</h3>
      ${highlights.length ? `
        <ul class="report-highlight-list">
          ${highlights.slice(0, 5).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}
        </ul>
      ` : `<p class="report-empty">No compact highlights were extracted from this report.</p>`}
      ${tables.length ? `
        <div class="brief-section-title">Compact table excerpts</div>
        ${tables.slice(0, 2).map(reportTable).join("")}
      ` : ""}
    </article>
  `;
}

function reportSection(section) {
  const reports = Array.isArray(section.reports) ? section.reports : [];
  return `
    <details class="report-panel">
      <summary>
        <span>
          <strong>${escapeHtml(section.title || "Latest report")}</strong>
          <small>${escapeHtml(section.updated_at || "waiting")}</small>
        </span>
        <em>${reports.length ? `${reports.length} source${reports.length > 1 ? "s" : ""}` : "no report yet"}</em>
      </summary>
      <div class="report-panel-body">
        <p>${escapeHtml(section.summary || "Latest web-formatted report digest.")}</p>
        ${reports.length ? reports.map(reportSourceCard).join("") : `
          <div class="report-empty">No latest report has been published for this slot yet.</div>
        `}
        <div class="brief-disclaimer">
          Compact public digest only. Not financial advice. Raw email text, repeated boilerplate,
          private recipients, secrets, local paths, infrastructure details, source links,
          and implementation internals are not published.
        </div>
      </div>
    </details>
  `;
}

function renderReportSections(payload) {
  const grid = document.getElementById("reportSectionGrid");
  const meta = document.getElementById("reportSectionMeta");
  if (!grid || !meta) return;
  const sections = Array.isArray(payload.report_sections) ? payload.report_sections : [];
  meta.textContent = sections.length
    ? `Published ${payload.published_at || "recently"} | ${sections.length} latest report panels`
    : "No report digests have been published yet.";
  grid.innerHTML = sections.length ? sections.map(reportSection).join("") : "";
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
    renderReportSections(payload);
    meta.textContent = `Published ${payload.published_at || "recently"} | ${briefs.length} sanitized surfaces | Private implementation withheld`;
    grid.innerHTML = briefs.length
      ? briefs.map(briefCard).join("")
      : "";
  } catch (error) {
    renderBriefPulse({ published_at: "waiting", scope: "no_public_snapshot" }, []);
    renderReportSections({ report_sections: [] });
    meta.textContent = "No public agent brief snapshot has been published yet.";
    grid.innerHTML = "";
  }
}

loadAgentBriefs();
