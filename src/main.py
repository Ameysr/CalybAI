import argparse
from pathlib import Path
from graph import PaperGraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def build_pipeline(topic, target=80):
    print(f"[1/3] Searching and crawling papers for: {topic}")
    graph = PaperGraph()
    graph.from_collector(topic, target=target)

    print(f"     Raw graph: {graph.node_count} papers, {graph.edge_count} citation edges")

    print("[2/3] Filtering to largest connected component...")
    graph = graph.largest_component()
    print(f"     Largest component: {graph.node_count} papers, {graph.edge_count} edges")

    print("[3/3] Saving graph to disk...")
    safe = topic.lower().replace(" ", "_").replace("-", "_")[:40]
    path = DATA_DIR / f"{safe}.json"
    graph.save(path)
    print(f"     Saved to {path}")

    return graph, path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Paper Onboarding Pipeline")
    parser.add_argument("--topic", default="Retrieval Augmented Generation", help="Research topic to crawl")
    parser.add_argument("--target", type=int, default=80, help="Target number of papers")
    args = parser.parse_args()

    build_pipeline(args.topic, args.target)
