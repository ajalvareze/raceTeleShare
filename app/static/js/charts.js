/**
 * charts.js — helpers for rendering telemetry channel charts via Chart.js
 */

const CHANNEL_COLORS = [
  "#e63946", "#457b9d", "#2a9d8f", "#e9c46a",
  "#f4a261", "#a8dadc", "#6d6875", "#b5838d",
];

/**
 * Render one canvas chart per telemetry channel.
 * @param {object} telemetryData  - TelemetryData schema object
 * @param {HTMLElement} container - grid container element
 */
function renderChannelCharts(telemetryData, container) {
  container.innerHTML = "";
  telemetryData.channels.forEach((ch, i) => {
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    wrap.innerHTML = `<h3>${ch.name}${ch.unit ? " (" + ch.unit + ")" : ""}</h3><canvas></canvas>`;
    container.appendChild(wrap);

    new Chart(wrap.querySelector("canvas"), {
      type: "line",
      data: {
        labels: ch.timestamps.map(t => t.toFixed(2)),
        datasets: [{
          label: ch.name,
          data: ch.data,
          borderColor: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
        }],
      },
      options: {
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxTicksLimit: 10, color: "#7a7d90" }, grid: { color: "#2a2d3a" } },
          y: { ticks: { color: "#7a7d90" }, grid: { color: "#2a2d3a" } },
        },
      },
    });
  });
}

/**
 * Render a delta-T chart comparing multiple laps against a reference.
 * @param {Array}        deltas    - array of LapDelta objects
 * @param {HTMLElement}  canvas    - canvas element
 */
function renderDeltaChart(deltas, canvas) {
  const datasets = deltas.map((d, i) => ({
    label: `Lap ${d.comparison_lap_id} vs Lap ${d.reference_lap_id}`,
    data: d.delta_seconds,
    borderColor: CHANNEL_COLORS[(i + 1) % CHANNEL_COLORS.length],
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.1,
    fill: false,
  }));

  new Chart(canvas, {
    type: "line",
    data: {
      labels: deltas[0]?.timestamps.map(t => t.toFixed(2)) ?? [],
      datasets,
    },
    options: {
      animation: false,
      plugins: {
        legend: { labels: { color: "#e0e0e8" } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y > 0 ? "+" : ""}${ctx.parsed.y.toFixed(3)}s`,
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 10, color: "#7a7d90" }, grid: { color: "#2a2d3a" } },
        y: {
          title: { display: true, text: "Delta (s)", color: "#7a7d90" },
          ticks: { color: "#7a7d90" },
          grid: { color: "#2a2d3a" },
        },
      },
    },
  });
}
