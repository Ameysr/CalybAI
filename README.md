# CalybAI — Research Paper Onboarding

An AI-powered citation network analyzer that maps a research field's paper relationships and generates structured reading curricula for new researchers. Converts raw OpenAlex paper metadata into ranked, dependency-respecting reading orders using NetworkX graph analysis and PageRank influence scoring.

Built to solve the problem that every new researcher faces: months spent piecing together a map of what is foundational, what builds on what, and what order makes sense to read.

## What It Does

Takes a research topic as input, crawls OpenAlex for papers and citation edges, builds a directed citation graph, computes influence metrics (PageRank, centrality, community clusters), and outputs a reading curriculum where foundational papers come first and recent work builds on earlier knowledge.

## Key Features

1. **OpenAlex API Crawler** — Fetches papers by semantic search query (up to 200 results). Collects referenced works ranked by citation frequency across seeds. Gathers citing papers via the `cites:` filter. Batch-resolves placeholder references with `openalex:` multi-ID filter (50 per call). No API key required, no rate limit.

2. **NetworkX Directed Graph** — Builds a DiGraph where `A → B` means "A cites B". Nodes store label, year, authors, citation count, and community assignment. Filters to the largest connected component to focus on the core citation network.

3. **PageRank Influence Scoring** — Computes nx.pagerank with α=0.85 across the citation graph. Results are cached via lazy initialization so no metric is computed more than once per pipeline run.

4. **Citation Depth Layering** — Each paper gets a "dependency depth" based on the longest path from root papers (papers with zero inbound citations). Within a layer, papers are sorted by year ascending (older first) then PageRank descending (most influential first).

5. **Foundational and Survey Detection** — Foundational papers are identified by a combined score of high PageRank + early reading position. Survey papers are identified by high out-degree (papers that survey many references).

6. **Interactive Web Dashboard** — FastAPI server with vis-network interactive citation graph showing paper nodes sized by PageRank, colored by community cluster, with highlighting, tooltips, zoom controls, and a detail sidebar. Reading curriculum view with checkable progress tracking persisted in localStorage. Stats dashboard with paper counts, graph density, clustering coefficient, and ranked lists.

7. **CSV and JSON Export** — Download the full reading order as CSV (rank, title, authors, year, citations, PageRank) or JSON for programmatic use.

## Architecture

```
                            User
                             |
                    [Browser / CLI]
                 HTML+JS  or  argparse
                             |
                        HTTP / REST
                             |
                     [FastAPI Server]
                     (server.py :8000)
                             |
                +------------+-----------+
                |                        |
          [Pipeline Runner]         [Memory Cache]
      (run_in_executor, async)   (thread-safe RLock)
                |
         [Analytical Pipeline — 5 Stages]
         1. Crawl    (OpenAlex API, keyword filter, ref ranking)
         2. Build    (NetworkX DiGraph, largest component)
         3. Analyze  (PageRank, degree, betweenness, communities)
         4. Order    (citation depth layering, topological sort)
         5. Export   (CSV, JSON, interactive graph JSON)
                |
      +---------+---------+---------+---------+
      |         |         |         |         |
  [OpenAlex]  [NetworkX] [Louvain]  [Vis.js]  [FastAPI]
    API        Graph      Cluster    Browser   REST
    Crawler    Engine     Detection  Render    Server
```

## Pipeline Deep Dive

| Stage | What It Does | Key Implementation Detail |
|-------|-------------|---------------------------|
| **Crawl** | Searches OpenAlex for topic papers (up to 50 seeds). Collects referenced works ranked by how many seeds cite them. Fetches citing papers. Batch-resolves placeholder references. | Keyword-overlap relevance filter excludes irrelevant papers. `target * 2` cap prevents unbounded growth. Batch fetch uses `openalex:id1\|id2\|...` filter (50 per call, 0.05s delay). |
| **Build** | Constructs NetworkX DiGraph from paper set. Nodes store metadata (title, year, authors, citation count). Edges represent citation direction. | `largest_component()` discards disconnected subgraphs. Graph persists to JSON for reuse. `add_citation` silently skips edges where either endpoint is missing. |
| **Analyze** | Computes PageRank (α=0.85), in-degree, out-degree, betweenness centrality (k-sampled at 100 for large graphs). Runs Louvain community detection. | All metric results cached via lazy init in Analyzer class. Betweenness skips graphs over 500 nodes. Falls back to greedy modularity if python-louvain not installed. |
| **Order** | Computes citation depth (longest path from root). Sorts by depth → year (asc) → PageRank (desc). Handles cycles via SCC condensation when topological sort fails. | `Curriculum` receives precomputed metrics from pipeline, never re-runs pagerank. Cycle resolution uses strongly connected components + condensed DAG. |
| **Export** | Returns reading order as ranked list with metadata. CSV export via `/api/export.csv`. JSON export via `/api/export.json`. Graph JSON with nodes/edges for frontend. | CSV generated server-side with proper quoting. JSON export returns full analysis results. Frontend uses `<a download>` for file downloads. |

## Running Instructions

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the web server
python server.py
```

Open **http://127.0.0.1:8000** in your browser, enter a research topic, and click **Run Analysis**. The pipeline will:
1. Crawl OpenAlex for 25+ papers on your topic
2. Build the citation graph
3. Compute influence metrics
4. Display the interactive graph, reading curriculum, and statistics

### CLI Mode (without browser)

```bash
python src/main.py --topic "Diffusion Models" --target 25
```

Outputs the same analysis directly to the terminal — reading order, foundational papers, surveys, and graph statistics.

### Docker Setup

```dockerfile
# Coming soon — single-command Docker Compose with all dependencies
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/run` | Run the full pipeline. Body: `{"topic": "...", "target": 25}`. Runs in background thread via `run_in_executor`. |
| GET | `/api/graph` | Return graph nodes and edges from the last run. |
| GET | `/api/reading-order` | Return ranked reading list with paper metadata. |
| GET | `/api/foundational` | Return top foundational papers by combined PageRank + rank score. |
| GET | `/api/surveys` | Return top survey papers by out-degree. |
| GET | `/api/paper/{id}` | Return metadata for a single paper by OpenAlex ID. |
| GET | `/api/status` | Return whether data is loaded and graph statistics. |
| GET | `/api/export.csv` | Download full reading order as CSV. |
| GET | `/api/export.json` | Download full analysis result as JSON. |
| GET | `/` | Serve the interactive web dashboard. |
| GET | `/docs` | Interactive Swagger API documentation. |

## Topics

`citation-network` `research-papers` `page-rank` `networkx` `reading-curriculum` `openalex` `graph-analysis` `vis-network`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Crawler | OpenAlex REST API (no auth, no rate limit) |
| Graph Engine | NetworkX 3.3 (DiGraph, PageRank, Louvain, betweenness) |
| Web Server | FastAPI (async, run_in_executor, RLock) |
| Frontend | Vanilla JS + vis-network 9.1 (interactive graph) |
| Icons | Lucide (clean SVG icon set) |
| Export | CSV (RFC 4180), JSON |
| ML Model Discovery | Not applicable — this is a graph analysis tool, not an ML pipeline |
