import argparse
from pipeline import run_pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Paper Onboarding")
    parser.add_argument("--topic", default="Retrieval Augmented Generation")
    parser.add_argument("--target", type=int, default=25)
    args = parser.parse_args()

    result = run_pipeline(args.topic, args.target)

    gs = result["stats"]
    print(f"\n=== {result['topic']} ===")
    print(f"Graph: {gs['node_count']} papers, {gs['edge_count']} edges")
    print(f"Density: {gs['density']}, Clustering: {gs['clustering']}")

    print("\n--- Top by PageRank ---")
    for s in sorted(result["graph"]["nodes"], key=lambda x: x["pagerank"], reverse=True)[:5]:
        print(f"  [{s['year']}] {s['title'][:60]} — PR={s['pagerank']}")

    print("\n--- Reading Order (first 10) ---")
    for p in result["reading_order"][:10]:
        print(f"  {p['rank']:3d}. [{p['year']}] {p['title'][:60]}")

    print("\n--- Foundational ---")
    for p in result["foundational"][:5]:
        print(f"  [{p['year']}] {p['title'][:60]} — PR={p['pagerank']}")

    print("\n--- Surveys ---")
    for p in result["surveys"]:
        print(f"  [{p['year']}] {p['title'][:60]} — {p['out_degree']} refs")
