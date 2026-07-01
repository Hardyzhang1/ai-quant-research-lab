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
