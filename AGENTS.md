# CalybAI — Research Paper Onboarding

## Project Context

A CLI tool that maps a research field's citation network and generates
reading curricula for new researchers.

### Architecture

- `src/collector.py` — OpenAlex API client. Searches papers, fetches
  references and citations, builds paper set and edge list.
- `src/graph.py` — NetworkX DiGraph wrapper. Manages papers dict,
  citation edges, save/load from JSON.
- `src/analyzer.py` — Graph metrics: PageRank, degree centrality,
  betweenness centrality, community detection (Louvain).
- `src/curriculum.py` — Generates reading order using citation depth
  layers, identifies foundational papers (PageRank + rank heuristic)
  and survey papers (out-degree).
- `src/main.py` — Pipeline entry point: crawl → build → analyze → print.

### Usage

```bash
python src/main.py --topic "Retrieval Augmented Generation" --target 80
```

### Data Flow

1. Search OpenAlex for topic → seed papers
2. Collect referenced works (most common across seeds) and citing works
3. Build NetworkX DiGraph (paper cites → paper)
4. Filter to largest connected component
5. Compute PageRank, degree, betweenness, communities
6. Generate reading order: citation depth → year (asc) → PageRank (desc)
7. Identify foundational papers (early depth + high PageRank) and surveys

### Key Design Decisions

- OpenAlex over Semantic Scholar: no rate limits, richer citation data
- Largest connected component: focuses on the core citation network
- Citation depth layering: each paper gets a "dependency depth" based
  on longest path from root papers; within a layer, older/influential
  papers are recommended first
