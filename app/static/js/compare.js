/**
 * compare.js — lap comparison page logic
 */
let deltaChartInstance = null;

async function runCompare() {
  const raw = document.getElementById("lap-ids-input").value;
  const lapIds = raw.split(",").map(s => parseInt(s.trim())).filter(Boolean);
  if (lapIds.length < 2) {
    alert("Enter at least 2 lap IDs separated by commas.");
    return;
  }

  const res = await fetch("/api/v1/laps/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ lap_ids: lapIds }),
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "Comparison failed");
    return;
  }

  const result = await res.json();

  // Delta chart
  if (result.deltas.length) {
    const wrap = document.getElementById("delta-chart-wrap");
    wrap.classList.remove("hidden");
    const canvas = document.getElementById("delta-canvas");
    if (deltaChartInstance) deltaChartInstance.destroy();
    deltaChartInstance = null;
    renderDeltaChart(result.deltas, canvas);
  }

  // Channel overlays — one chart per channel, all laps overlaid
  const container = document.getElementById("channel-charts");
  container.innerHTML = "";

  result.channels_available.forEach((chName, ci) => {
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    wrap.innerHTML = `<h3>${chName}</h3><canvas></canvas>`;
    container.appendChild(wrap);

    const datasets = result.laps.map((lapData, li) => {
      const ch = lapData.channels.find(c => c.name === chName);
      if (!ch) return null;
      return {
        label: `Lap ${lapData.lap_id}`,
        data: ch.data,
        borderColor: CHANNEL_COLORS[li % CHANNEL_COLORS.length],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      };
    }).filter(Boolean);

    const timestamps = result.laps[0]?.channels.find(c => c.name === chName)?.timestamps ?? [];

    new Chart(wrap.querySelector("canvas"), {
      type: "line",
      data: {
        labels: timestamps.map(t => t.toFixed(2)),
        datasets,
      },
      options: {
        animation: false,
        plugins: { legend: { labels: { color: "#e0e0e8" } } },
        scales: {
          x: { ticks: { maxTicksLimit: 10, color: "#7a7d90" }, grid: { color: "#2a2d3a" } },
          y: { ticks: { color: "#7a7d90" }, grid: { color: "#2a2d3a" } },
        },
      },
    });
  });
}
