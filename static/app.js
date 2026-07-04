let network = null;
let currentGraph = null;
let currentTopic = "";
let nodesDataSet = null;
let edgesDataSet = null;
let selectedNodeId = null;
let physicsEnabled = true;

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

  // Graph floating controls
  document.getElementById("zoomInBtn").addEventListener("click", () => {
    if (network) network.moveTo({ scale: network.getScale() * 1.3, animation: true });
  });
  document.getElementById("zoomOutBtn").addEventListener("click", () => {
    if (network) network.moveTo({ scale: network.getScale() / 1.3, animation: true });
  });
  document.getElementById("zoomFitBtn").addEventListener("click", () => {
    if (network) network.fit({ animation: true });
  });
  document.getElementById("physicsBtn").addEventListener("click", togglePhysics);

  // Load initial icons
  lucide.createIcons();
});

async function checkStatus() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    if (s.loaded) {
      currentTopic = s.topic;
      updateStatusBar(s.topic, s.stats.node_count, s.stats.edge_count);
      enableExports();
      await Promise.all([loadGraph(), loadReading(), loadStats()]);
    }
  } catch {}
}

function updateStatusBar(topic, nodeCount, edgeCount) {
  const el = document.getElementById("statusBar");
  el.className = "status-wrapper status-loaded";
  el.innerHTML = `
    <span class="status-dot"></span>
    <span class="status-text">Loaded: ${topic} — ${nodeCount} papers, ${edgeCount} edges</span>
  `;
}

function setErrorStatus(msg) {
  const el = document.getElementById("statusBar");
  el.className = "status-wrapper status-error";
  el.innerHTML = `
    <span class="status-dot"></span>
    <span class="status-text">${msg}</span>
  `;
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
    position: "fixed", bottom: "24px", right: "24px", padding: "12px 24px",
    borderRadius: "8px", color: "#fff", fontSize: "13px", zIndex: 1000,
    fontWeight: "600",
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    background: isError ? "linear-gradient(135deg, #ef4444, #b91c1c)" : "linear-gradient(135deg, #d97706, #b45309)",
    boxShadow: "0 10px 25px rgba(0,0,0,0.4)", transition: "all 0.3s ease",
  });
  document.body.appendChild(div);
  setTimeout(() => { div.style.opacity = "0"; div.style.transform = "translateY(10px)"; setTimeout(() => div.remove(), 300); }, 3000);
}

function showSpinner(v, msg = "Analyzing Network...") {
  const spinner = document.getElementById("spinner");
  document.getElementById("spinner-msg").textContent = msg;
  spinner.style.display = v ? "flex" : "none";
}

async function runAnalysis() {
  const topic = document.getElementById("topicInput").value.trim();
  const target = parseInt(document.getElementById("targetInput").value) || 80;
  if (!topic) return showToast("Enter a topic to analyze", true);

  showSpinner(true, `Crawling OpenAlex for papers on "${topic}"...`);
  setErrorStatus("Crawling " + topic + "...");

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
    currentTopic = data.topic;
    const s = data.stats;
    updateStatusBar(data.topic, s.node_count, s.edge_count);
    enableExports();
    showToast(`Analysis complete: ${s.node_count} papers loaded`);
    await Promise.all([loadGraph(), loadReading(), loadStats()]);
    switchTab("graph");
  } catch (e) {
    setErrorStatus("Error: " + e.message);
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

// Sophisticated warm scholarly colors for citation graph communities
const palette = [
  "#d97706", // Amber / Bronze
  "#14b8a6", // Teal
  "#ec4899", // Deep Rose
  "#84cc16", // Sage Green
  "#a855f7", // Soft Purple
  "#fb923c", // Warm Copper
  "#06b6d4", // Clean Cyan
  "#f43f5e"  // Crimson
];

function getCommunityColor(index) {
  return palette[index % palette.length];
}

function renderGraph(graphData) {
  const container = document.getElementById("graph-container");
  container.innerHTML = "";

  const maxPr = Math.max(...graphData.nodes.map(n => n.pagerank), 0.001);

  // Structure Vis data sets
  nodesDataSet = new vis.DataSet(graphData.nodes.map(n => {
    const nodeColor = getCommunityColor(n.community);
    
    // Custom rich HTML tooltip matching the warm academic theme
    const tooltipEl = document.createElement("div");
    tooltipEl.innerHTML = `
      <div style="font-weight: 700; font-size: 13px; color: #f5f4f2; margin-bottom: 4px;">${n.title}</div>
      <div style="font-size: 11px; color: #c5c1bb; margin-bottom: 6px;">${n.authors} (${n.year || "?"})</div>
      <div style="display: flex; gap: 8px; font-size: 11px; font-weight: 600; color: #f59e0b;">
        <span>Citations: ${n.citations}</span>
        <span>PageRank: ${n.pagerank.toFixed(4)}</span>
      </div>
    `;

    return {
      id: n.id,
      shape: "dot",
      label: (n.title || "?").slice(0, 24) + ((n.title || "").length > 24 ? "..." : ""),
      title: tooltipEl,
      size: 10 + 26 * Math.sqrt(n.pagerank / maxPr),
      color: {
        background: nodeColor,
        border: "rgba(10, 9, 8, 0.8)",
        highlight: {
          background: nodeColor,
          border: "#ffffff"
        },
        hover: {
          background: nodeColor,
          border: "#f59e0b"
        }
      },
      font: {
        color: "#c5c1bb",
        size: 11,
        face: "Plus Jakarta Sans",
        strokeWidth: 2,
        strokeColor: "#060504"
      },
      borderWidth: 1.5,
      borderWidthSelected: 3,
      shadow: {
        enabled: true,
        color: "rgba(0,0,0,0.5)",
        size: 6,
        x: 0,
        y: 3
      }
    };
  }));

  edgesDataSet = new vis.DataSet(graphData.edges.map(e => ({
    id: `${e.from}->${e.to}`,
    from: e.from,
    to: e.to,
    arrows: "to",
    color: {
      color: "#413b34",
      highlight: "#f59e0b",
      hover: "#f59e0b",
      opacity: 0.4
    },
    width: 0.8,
    smooth: { type: "continuous" }
  })));

  const options = {
    physics: {
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: -36,
        centralGravity: 0.015,
        springLength: 80,
        springConstant: 0.08
      },
      stabilization: {
        iterations: 150,
        updateInterval: 25
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      zoomView: true
    }
  };

  network = new vis.Network(container, { nodes: nodesDataSet, edges: edgesDataSet }, options);

  // Network event handlers
  network.on("click", params => {
    if (params.nodes.length > 0) {
      const pid = params.nodes[0];
      selectedNodeId = pid;
      showPaperDetail(pid);
      highlightNeighbors(pid);
      network.focus(pid, {
        scale: Math.max(network.getScale(), 0.95),
        animation: { duration: 600, easingFunction: "easeInOutQuad" }
      });
    } else {
      selectedNodeId = null;
      hidePaperDetail();
      resetHighlighting();
    }
  });

  network.on("stabilizationIterationsDone", () => {
    // Once graph stabilizes, turn off physics to optimize performance
    if (physicsEnabled) {
      physicsEnabled = false;
      network.setOptions({ physics: { enabled: false } });
      const pBtn = document.getElementById("physicsBtn");
      pBtn.classList.remove("active");
      pBtn.title = "Enable Physics Layout";
    }
  });
}

function togglePhysics() {
  physicsEnabled = !physicsEnabled;
  network.setOptions({ physics: { enabled: physicsEnabled } });
  const pBtn = document.getElementById("physicsBtn");
  if (physicsEnabled) {
    pBtn.classList.add("active");
    pBtn.title = "Pause Physics Layout";
    network.stabilize();
  } else {
    pBtn.classList.remove("active");
    pBtn.title = "Enable Physics Layout";
  }
}

// Highlight connected nodes and edges, dim others
function highlightNeighbors(selectedId) {
  const connectedNodes = network.getConnectedNodes(selectedId);
  const connectedEdges = network.getConnectedEdges(selectedId);
  
  const allNodes = nodesDataSet.get();
  const allEdges = edgesDataSet.get();

  const updateNodes = [];
  const updateEdges = [];

  allNodes.forEach(node => {
    const isSelected = node.id === selectedId;
    const isNeighbor = connectedNodes.includes(node.id);
    
    if (isSelected) {
      updateNodes.push({
        id: node.id,
        color: { border: "#ffffff" },
        font: { color: "#ffffff", size: 12 }
      });
    } else if (isNeighbor) {
      updateNodes.push({
        id: node.id,
        color: { opacity: 1.0 },
        font: { color: "#f5f4f2", size: 11 }
      });
    } else {
      // Dim non-neighbors
      updateNodes.push({
        id: node.id,
        color: {
          background: "rgba(30, 27, 24, 0.25)",
          border: "rgba(65, 59, 52, 0.15)"
        },
        font: { color: "rgba(197, 193, 187, 0.15)", size: 10 }
      });
    }
  });

  allEdges.forEach(edge => {
    const isConnected = connectedEdges.includes(edge.id);
    if (isConnected) {
      updateEdges.push({
        id: edge.id,
        color: { color: "#f59e0b", opacity: 0.8 },
        width: 1.5
      });
    } else {
      updateEdges.push({
        id: edge.id,
        color: { color: "#1e1b18", opacity: 0.05 },
        width: 0.4
      });
    }
  });

  nodesDataSet.update(updateNodes);
  edgesDataSet.update(updateEdges);
}

function resetHighlighting() {
  if (!currentGraph || !nodesDataSet || !edgesDataSet) return;

  const maxPr = Math.max(...currentGraph.nodes.map(n => n.pagerank), 0.001);
  
  const originalNodes = currentGraph.nodes.map(n => {
    const nodeColor = getCommunityColor(n.community);
    return {
      id: n.id,
      color: {
        background: nodeColor,
        border: "rgba(10, 9, 8, 0.8)",
        highlight: { background: nodeColor, border: "#ffffff" },
        hover: { background: nodeColor, border: "#f59e0b" }
      },
      font: { color: "#c5c1bb", size: 11 }
    };
  });

  const originalEdges = currentGraph.edges.map(e => ({
    id: `${e.from}->${e.to}`,
    color: {
      color: "#413b34",
      opacity: 0.4
    },
    width: 0.8
  }));

  nodesDataSet.update(originalNodes);
  edgesDataSet.update(originalEdges);
}

// Local Storage helper for checked reading list
function getReadPapersKey() {
  return `calybai_read_${currentTopic.replace(/[^a-zA-Z0-9]/g, "_")}`;
}

function getReadPapers() {
  try {
    return JSON.parse(localStorage.getItem(getReadPapersKey())) || [];
  } catch {
    return [];
  }
}

function togglePaperRead(pid) {
  const readList = getReadPapers();
  const idx = readList.indexOf(pid);
  if (idx > -1) {
    readList.splice(idx, 1);
    showToast("Paper marked as unread");
  } else {
    readList.push(pid);
    showToast("Paper marked as read!");
  }
  localStorage.setItem(getReadPapersKey(), JSON.stringify(readList));
  
  // Refresh views
  updateReadingProgress(readList);
  updateReadingItemUI(pid, idx === -1);
  
  // If details panel shows this paper, update its button
  if (selectedNodeId === pid) {
    showPaperDetail(pid);
  }
}

function updateReadingItemUI(pid, isRead) {
  const items = document.querySelectorAll(`.reading-item[data-id="${pid}"]`);
  items.forEach(el => {
    el.classList.toggle("completed", isRead);
  });
}

function updateReadingProgress(readList) {
  const total = currentGraph ? currentGraph.nodes.length : 0;
  const count = readList.filter(id => currentGraph && currentGraph.nodes.some(n => n.id === id)).length;
  
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  
  document.getElementById("progress-percent").textContent = `${pct}%`;
  document.getElementById("progress-bar-fill").style.width = `${pct}%`;
  document.getElementById("progress-stats-text").textContent = `${count} of ${total} papers read`;
}

async function showPaperDetail(pid) {
  try {
    const r = await fetch(`/api/paper/${encodeURIComponent(pid)}`);
    const p = await r.json();
    const div = document.getElementById("detail-content");
    const empty = document.getElementById("detail-empty");

    const readList = getReadPapers();
    const isRead = readList.includes(pid);
    
    const [found, surv] = await Promise.all([
      fetch("/api/foundational").then(res => res.json()),
      fetch("/api/surveys").then(res => res.json()),
    ]);
    const isFound = found.some(f => f.id === pid);
    const isSurv = surv.some(s => s.id === pid);

    const badges = [];
    if (isFound) badges.push('<span class="detail-tag badge-foundational"><i data-lucide="award"></i>Foundational</span>');
    if (isSurv) badges.push('<span class="detail-tag badge-survey"><i data-lucide="compass"></i>Survey</span>');

    const cleanAlexId = p.id.replace("https://openalex.org/", "");

    div.innerHTML = `
      <div class="detail-header">
        <h3>${p.title}</h3>
        <div class="detail-tags">
          <span class="detail-tag"><i data-lucide="calendar"></i>${p.year || "?"}</span>
          ${badges.join("")}
        </div>
      </div>

      <div class="detail-body-section">
        <h4>Authors</h4>
        <div class="authors-list">${p.authors}</div>
      </div>

      <div class="detail-body-section">
        <h4>Key Metrics</h4>
        <div class="metrics-row">
          <div class="metric-box">
            <span class="val">${p.citations.toLocaleString()}</span>
            <span class="lbl">Citations</span>
          </div>
          <div class="metric-box">
            <span class="val">${p.pagerank.toFixed(4)}</span>
            <span class="lbl">PageRank</span>
          </div>
          <div class="metric-box" style="margin-top:8px; grid-column: span 2;">
            <span class="val" style="font-size:14px;color:#c5c1bb">
              Cites: ${p.in_degree} &bull; References: ${p.out_degree}
            </span>
            <span class="lbl">Connection Degree</span>
          </div>
        </div>
      </div>

      <div class="detail-body-section">
        <h4>System ID</h4>
        <div class="detail-id-card">${cleanAlexId}</div>
      </div>

      <div class="detail-actions">
        <button id="toggleReadBtn" class="btn ${isRead ? 'btn-secondary' : 'btn-accent'}">
          <i data-lucide="${isRead ? 'rotate-ccw' : 'check-circle-2'}"></i>
          <span>${isRead ? 'Mark as Unread' : 'Mark as Read'}</span>
        </button>
        <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(p.title)}" target="_blank" class="btn btn-outline" style="text-decoration:none">
          <i data-lucide="external-link"></i>
          <span>Google Scholar</span>
        </a>
        <a href="${p.id}" target="_blank" class="btn btn-outline" style="text-decoration:none">
          <i data-lucide="database"></i>
          <span>OpenAlex Record</span>
        </a>
      </div>
    `;

    // Hook events
    document.getElementById("toggleReadBtn").addEventListener("click", () => togglePaperRead(pid));

    empty.style.display = "none";
    div.style.display = "block";
    
    lucide.createIcons();
  } catch (err) {
    hidePaperDetail();
  }
}

function hidePaperDetail() {
  document.getElementById("detail-empty").style.display = "flex";
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

    const readList = getReadPapers();

    const list = document.getElementById("reading-list");
    list.innerHTML = ro.slice(0, 200).map(p => {
      const isFound = foundIds.has(p.id);
      const isSurv = survIds.has(p.id);
      const isCompleted = readList.includes(p.id);

      const badges = [];
      if (isFound) badges.push('<span class="detail-tag badge-foundational" style="font-size: 10px; padding: 1px 5px;"><i data-lucide="award" style="width:10px;height:10px"></i>Foundational</span>');
      if (isSurv) badges.push('<span class="detail-tag badge-survey" style="font-size: 10px; padding: 1px 5px;"><i data-lucide="compass" style="width:10px;height:10px"></i>Survey</span>');

      return `
        <div class="reading-item ${isCompleted ? 'completed' : ''}" data-id="${p.id}">
          <div class="reading-timeline-control">
            <div class="reading-checkbox-label" onclick="event.stopPropagation(); togglePaperRead('${p.id}')">
              <i data-lucide="check"></i>
            </div>
            <span class="rank-badge">#${p.rank}</span>
          </div>
          
          <div class="reading-info-wrapper" onclick="jumpToGraphNode('${p.id}')">
            <div class="reading-title-row">
              <span class="title">${p.title}</span>
              <span class="badges">${badges.join("")}</span>
            </div>
            <div class="reading-metadata-row">
              <span><i data-lucide="users"></i>${(p.authors || "Unknown").slice(0, 60)}${p.authors && p.authors.length > 60 ? '...' : ''}</span>
              <span><i data-lucide="calendar"></i>${p.year || "?"}</span>
              <span><i data-lucide="trending-up"></i>${p.citations} citations</span>
              <span><i data-lucide="bar-chart-2"></i>PR: ${p.pagerank.toFixed(4)}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    updateReadingProgress(readList);
    lucide.createIcons();
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
      <div class="stat-grid">
        <div class="stat-item"><div class="value">${s.node_count}</div><div class="label">Total Papers</div></div>
        <div class="stat-item"><div class="value">${s.edge_count}</div><div class="label">Citation Links</div></div>
        <div class="stat-item"><div class="value">${s.density.toFixed(4)}</div><div class="label">Graph Density</div></div>
        <div class="stat-item"><div class="value">${s.clustering.toFixed(4)}</div><div class="label">Clustering Coeff</div></div>
      </div>

      <div class="stats-cards-grid">
        <div class="stat-card">
          <h3><i data-lucide="sparkles"></i>Top by PageRank (Influence)</h3>
          <div class="stat-list">
            ${topPr.map((p, idx) => `
              <div class="stat-list-item" onclick="jumpToGraphNode('${p.id}')" style="cursor:pointer">
                <span class="stat-list-index">${idx + 1}</span>
                <div class="stat-list-content">
                  <div class="stat-list-title">${p.title}</div>
                  <div class="stat-list-meta">${p.year} &bull; PR: ${p.pagerank.toFixed(4)} &bull; ${p.citations} citations</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="stat-card">
          <h3><i data-lucide="trending-up"></i>Top by Citation Count</h3>
          <div class="stat-list">
            ${topCit.map((p, idx) => `
              <div class="stat-list-item" onclick="jumpToGraphNode('${p.id}')" style="cursor:pointer">
                <span class="stat-list-index">${idx + 1}</span>
                <div class="stat-list-content">
                  <div class="stat-list-title">${p.title}</div>
                  <div class="stat-list-meta">${p.year} &bull; ${p.citations} citations &bull; PR: ${p.pagerank.toFixed(4)}</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="stat-card">
          <h3><i data-lucide="award"></i>Foundational Papers</h3>
          <div class="stat-list">
            ${foundR.slice(0, 5).map((p, idx) => `
              <div class="stat-list-item" onclick="jumpToGraphNode('${p.id}')" style="cursor:pointer">
                <span class="stat-list-index">${idx + 1}</span>
                <div class="stat-list-content">
                  <div class="stat-list-title">${p.title}</div>
                  <div class="stat-list-meta">${p.year} &bull; PR: ${p.pagerank.toFixed(4)} &bull; Cites: ${p.in_degree}</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="stat-card">
          <h3><i data-lucide="compass"></i>Key Survey Papers</h3>
          <div class="stat-list">
            ${survR.slice(0, 5).map((p, idx) => `
              <div class="stat-list-item" onclick="jumpToGraphNode('${p.id}')" style="cursor:pointer">
                <span class="stat-list-index">${idx + 1}</span>
                <div class="stat-list-content">
                  <div class="stat-list-title">${p.title}</div>
                  <div class="stat-list-meta">${p.year} &bull; References out: ${p.out_degree} &bull; Cites in: ${p.in_degree}</div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>
    `;
    lucide.createIcons();
  } catch {}
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.toggle("active", t.id === "tab-" + name));
  if (name === "graph" && network) {
    setTimeout(() => {
      network.fit();
    }, 100);
  }
}

function jumpToGraphNode(pid) {
  switchTab("graph");
  if (network && nodesDataSet) {
    setTimeout(() => {
      selectedNodeId = pid;
      network.selectNodes([pid]);
      showPaperDetail(pid);
      highlightNeighbors(pid);
      network.focus(pid, {
        scale: 1.1,
        animation: { duration: 800, easingFunction: "easeInOutQuad" }
      });
    }, 200);
  }
}

function exportFile(fmt) {
  window.open(`/api/export.${fmt}`, "_blank");
}
