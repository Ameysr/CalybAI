let network = null;
let currentGraph = null;

document.addEventListener("DOMContentLoaded", () => {
  checkStatus();

  document.getElementById("runBtn").addEventListener("click", runAnalysis);
  document.getElementById("exportCsvBtn").addEventListener("click", () => exportFile("csv"));
  document.getElementById("exportJsonBtn").addEventListener("click", () => exportFile("json"));

  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => switchTab(t.dataset.tab));
  });

  document.getElementById("topicInput").addEventListener("keydown", e => {
    if (e.key === "Enter") runAnalysis();
  });
});

async function checkStatus() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    if (s.loaded) {
      setStatus(`Loaded: ${s.topic} — ${s.stats.node_count} papers, ${s.stats.edge_count} edges`);
      enableExports();
      await Promise.all([loadGraph(), loadReading(), loadStats()]);
    }
  } catch {}
}

function setStatus(msg, isError) {
  const el = document.getElementById("statusBar");
  el.textContent = msg;
  el.style.color = isError ? "#f87171" : "#94a3b8";
}

function enableExports() {
  document.getElementById("exportCsvBtn").disabled = false;
  document.getElementById("exportJsonBtn").disabled = false;
}

function showToast(msg, isError) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const div = document.createElement("div");
  div.className = "toast";
  div.textContent = msg;
  Object.assign(div.style, {
    position: "fixed", bottom: "20px", right: "20px", padding: "12px 20px",
    borderRadius: "6px", color: "#fff", fontSize: "13px", zIndex: 200,
    background: isError ? "#ef4444" : "#22c55e",
    boxShadow: "0 2px 8px rgba(0,0,0,0.2)", transition: "opacity 0.3s",
  });
  document.body.appendChild(div);
  setTimeout(() => { div.style.opacity = "0"; setTimeout(() => div.remove(), 300); }, 3000);
}

function showSpinner(v) {
  document.getElementById("spinner").style.display = v ? "flex" : "none";
}

async function runAnalysis() {
  const topic = document.getElementById("topicInput").value.trim();
  const target = parseInt(document.getElementById("targetInput").value) || 80;
  if (!topic) return showToast("Enter a topic", true);

  showSpinner(true);
  setStatus("Crawling " + topic + "...");

  try {
    const r = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, target }),
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || "Analysis failed");
    }
    const data = await r.json();
    const s = data.stats;
    setStatus(`Loaded: ${data.topic} — ${s.node_count} papers, ${s.edge_count} edges`);
    enableExports();
    showToast(`Analysis complete: ${s.node_count} papers, ${s.edge_count} citation edges`);
    await Promise.all([loadGraph(), loadReading(), loadStats()]);
    switchTab("graph");
  } catch (e) {
    setStatus("Error: " + e.message, true);
    showToast(e.message, true);
  } finally {
    showSpinner(false);
  }
}

async function loadGraph() {
  try {
    const r = await fetch("/api/graph");
    currentGraph = await r.json();
    renderGraph(currentGraph);
  } catch {}
}

function renderGraph(graphData) {
  const container = document.getElementById("graph-container");
  container.innerHTML = "";

  const maxPr = Math.max(...graphData.nodes.map(n => n.pagerank), 0.001);
  const palette = ["#3b82f6","#ef4444","#22c55e","#f59e0b","#8b5cf6","#ec4899","#14b8a6","#f97316"];

  const nodes = new vis.DataSet(graphData.nodes.map(n => ({
    id: n.id,
    label: (n.title || "?").slice(0, 28),
    title: `${n.title}\n${n.authors} (${n.year || "?"})`,
    size: 8 + 24 * Math.sqrt(n.pagerank / maxPr),
    color: { background: palette[n.community % palette.length], border: "#1e293b" },
    borderWidth: 1,
    font: { size: 10 },
  })));

  const edges = new vis.DataSet(graphData.edges.map(e => ({
    from: e.from,
    to: e.to,
    arrows: "to",
    color: { color: "#94a3b8", opacity: 0.4 },
    width: 0.5,
  })));

  const options = {
    physics: { solver: "forceAtlas2Based", stabilization: { iterations: 150 } },
    interaction: { hover: true, tooltipDelay: 200 },
    edges: { smooth: { type: "continuous" } },
  };

  network = new vis.Network(container, { nodes, edges }, options);

  network.on("click", params => {
    if (params.nodes.length > 0) {
      showPaperDetail(params.nodes[0]);
    } else {
      hidePaperDetail();
    }
  });
}

async function showPaperDetail(pid) {
  try {
    const r = await fetch(`/api/paper/${encodeURIComponent(pid)}`);
    const p = await r.json();
    const div = document.getElementById("detail-content");
    const empty = document.getElementById("detail-empty");

    const badge = p.pagerank > 0.01 ? '<span class="badge badge-foundational">High Influence</span>' : "";
    div.innerHTML = `
      <h3>${p.title}</h3>
      <div class="meta">
        <span>${p.authors}</span>
        <span>${p.year || "?"}</span>
        <span>${p.citations} citations</span>
        <span>PR: ${p.pagerank}</span>
        ${badge}
      </div>
      <div style="font-size:12px;color:#475569;line-height:1.6">
        <p><strong>In-degree:</strong> ${p.in_degree} papers cite this</p>
        <p><strong>Out-degree:</strong> ${p.out_degree} references</p>
        <p style="word-break:break-all;font-size:11px;margin-top:8px;color:#94a3b8">${p.id.replace("https://openalex.org/", "")}</p>
      </div>
    `;
    empty.style.display = "none";
    div.style.display = "block";
  } catch {
    hidePaperDetail();
  }
}

function hidePaperDetail() {
  document.getElementById("detail-empty").style.display = "block";
  document.getElementById("detail-content").style.display = "none";
}

async function loadReading() {
  try {
    const [ro, found, surv] = await Promise.all([
      fetch("/api/reading-order").then(r => r.json()),
      fetch("/api/foundational").then(r => r.json()),
      fetch("/api/surveys").then(r => r.json()),
    ]);

    const foundIds = new Set(found.map(f => f.id));
    const survIds = new Set(surv.map(s => s.id));

    const list = document.getElementById("reading-list");
    list.innerHTML = ro.slice(0, 200).map(p => {
      const badges = [];
      if (foundIds.has(p.id)) badges.push('<span class="badge badge-foundational">Foundational</span>');
      if (survIds.has(p.id)) badges.push('<span class="badge badge-survey">Survey</span>');
      return `
        <div class="reading-item">
          <div class="rank">${p.rank}</div>
          <div class="info">
            <div class="title">${p.title} ${badges.join(" ")}</div>
            <div class="meta">${p.authors} — ${p.year || "?"} — ${p.citations} cites — PR: ${p.pagerank}</div>
          </div>
        </div>
      `;
    }).join("");
  } catch {}
}

async function loadStats() {
  try {
    const [statusR, foundR, survR, graphR] = await Promise.all([
      fetch("/api/status").then(r => r.json()),
      fetch("/api/foundational").then(r => r.json()),
      fetch("/api/surveys").then(r => r.json()),
      fetch("/api/graph").then(r => r.json()),
    ]);

    const s = statusR.stats;
    const topPr = [...graphR.nodes].sort((a, b) => b.pagerank - a.pagerank).slice(0, 5);
    const topCit = [...graphR.nodes].sort((a, b) => b.citations - a.citations).slice(0, 5);

    document.getElementById("stats-content").innerHTML = `
      <div class="stat-card">
        <div class="stat-grid">
          <div class="stat-item"><div class="value">${s.node_count}</div><div class="label">Papers</div></div>
          <div class="stat-item"><div class="value">${s.edge_count}</div><div class="label">Citation Edges</div></div>
          <div class="stat-item"><div class="value">${s.density}</div><div class="label">Density</div></div>
          <div class="stat-item"><div class="value">${s.clustering}</div><div class="label">Clustering</div></div>
        </div>
      </div>

      <div class="stat-card">
        <h3>Top by PageRank (Influence)</h3>
        ${topPr.map(p => `<div style="padding:4px 0;font-size:13px"><strong>[${p.year}]</strong> ${(p.title || "?").slice(0, 70)} <span style="color:#64748b">— PR=${p.pagerank}</span></div>`).join("")}
      </div>

      <div class="stat-card">
        <h3>Top by Citation Count</h3>
        ${topCit.map(p => `<div style="padding:4px 0;font-size:13px"><strong>[${p.year}]</strong> ${(p.title || "?").slice(0, 70)} <span style="color:#64748b">— ${p.citations} cites</span></div>`).join("")}
      </div>

      <div class="stat-card">
        <h3>Foundational Papers</h3>
        ${foundR.map(p => `<div style="padding:4px 0;font-size:13px"><strong>[${p.year}]</strong> ${(p.title || "?").slice(0, 70)} <span style="color:#64748b">— PR=${p.pagerank}</span></div>`).join("")}
      </div>

      <div class="stat-card">
        <h3>Survey Papers</h3>
        ${survR.map(p => `<div style="padding:4px 0;font-size:13px"><strong>[${p.year}]</strong> ${(p.title || "?").slice(0, 70)} <span style="color:#64748b">— ${p.out_degree} refs</span></div>`).join("")}
      </div>
    `;
  } catch {}
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.toggle("active", t.id === "tab-" + name));
  if (name === "graph" && network) {
    setTimeout(() => network.fit(), 100);
  }
}

function exportFile(fmt) {
  window.open(`/api/export.${fmt}`, "_blank");
}
