import argparse
import networkx as nx
from pathlib import Path
from graph import PaperGraph
from analyzer import Analyzer
from curriculum import Curriculum

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def build_pipeline(topic, target=80):
    print(f"[1/3] Crawling papers for: {topic}")
    graph = PaperGraph()
    graph.from_collector(topic, target=target)
    print(f"     Raw graph: {graph.node_count} papers, {graph.edge_count} edges")

    print("[2/3] Filtering to largest connected component...")
    graph = graph.largest_component()
    print(f"     Component: {graph.node_count} papers, {graph.edge_count} edges")

    print("[3/3] Saving...")
    safe = topic.lower().replace(" ", "_").replace("-", "_")[:40]
    path = DATA_DIR / f"{safe}.json"
    graph.save(path)
    print(f"     Saved to {path}")
    return graph, path

def analyze_pipeline(graph):
    print("\n[Analysis] Computing metrics...")
    analyzer = Analyzer(graph)

    stats = analyzer.stats()
    pr = {s["id"]: s["pagerank"] for s in stats}

    top_pr = sorted(stats, key=lambda x: x["pagerank"], reverse=True)[:5]
    print("\n--- Top Papers by PageRank (Influence) ---")
    for s in top_pr:
        yr = s["year"] or "?"
        print(f"  [{yr}] {s['title'][:60]} — PR={s['pagerank']}")

    top_cited = sorted(stats, key=lambda x: x["citations"], reverse=True)[:5]
    print("\n--- Top Papers by Citation Count ---")
    for s in top_cited:
        yr = s["year"] or "?"
        print(f"  [{yr}] {s['title'][:60]} — {s['citations']} cites")

    print("\n--- Graph Summary ---")
    print(f"  Nodes: {len(stats)}")
    print(f"  Edges: {graph.edge_count}")
    avg_cc = nx.average_clustering(graph.graph.to_undirected())
    print(f"  Avg clustering: {avg_cc:.3f}")
    print(f"  Density: {nx.density(graph.graph):.4f}")

    print("\n[Curriculum] Generating reading order...")
    curriculum = Curriculum(graph, analyzer)
    reading, has_cycles = curriculum.reading_order()

    print("\n--- Reading Order (first 10 papers) ---")
    for p in reading[:10]:
        yr = p["year"] or "?"
        print(f"  {p['rank']:3d}. [{yr}] {p['title'][:60]}")

    if has_cycles:
        print("  (Note: citation graph had cycles; resolved via SCC condensation)")

    foundational = curriculum.foundational_papers(top_n=5)
    print("\n--- Foundational Papers (read first) ---")
    for p in foundational:
        yr = p["year"] or "?"
        print(f"  [{yr}] {p['title'][:60]} — PR={p['pagerank']}")

    surveys = curriculum.survey_papers(top_n=3)
    print("\n--- Survey / Overview Papers ---")
    for p in surveys:
        yr = p["year"] or "?"
        print(f"  [{yr}] {p['title'][:60]} — {p['out_degree']} refs")

    return curriculum, reading

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Paper Onboarding Pipeline")
    parser.add_argument("--topic", default="Retrieval Augmented Generation")
    parser.add_argument("--target", type=int, default=80)
    args = parser.parse_args()

    graph, path = build_pipeline(args.topic, args.target)
    analyze_pipeline(graph)
