from pathlib import Path
import networkx as nx
from graph import PaperGraph
from analyzer import Analyzer
from curriculum import Curriculum

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def run_pipeline(topic, target=25):
    graph = PaperGraph()
    graph.from_collector(topic, target=target)
    graph = graph.largest_component()

    analyzer = Analyzer(graph)
    pr = analyzer.pagerank()
    in_deg, out_deg = analyzer.degree_metrics()
    communities = analyzer.detect_communities()

    curriculum = Curriculum(graph, pr, in_deg, out_deg)
    reading, has_cycles = curriculum.reading_order()
    foundational = curriculum.foundational_papers(top_n=10)
    surveys = curriculum.survey_papers(top_n=5)

    safe = topic.lower().replace(" ", "_").replace("-", "_")[:40]
    path = DATA_DIR / f"{safe}.json"
    graph.save(path)

    nodes = []
    for pid, p in graph.papers.items():
        nodes.append({
            "id": pid,
            "title": p.get("title", "Untitled"),
            "authors": p.get("authors", "Unknown"),
            "year": p.get("year"),
            "citations": p.get("cited_by_count", 0),
            "community": communities.get(pid, 0),
            "pagerank": round(pr.get(pid, 0), 6),
            "in_degree": in_deg.get(pid, 0),
            "out_degree": out_deg.get(pid, 0),
        })

    edges = [{"from": u, "to": v} for u, v in graph.graph.edges()]

    return {
        "topic": topic,
        "graph": {"nodes": nodes, "edges": edges},
        "reading_order": reading,
        "foundational": foundational,
        "surveys": surveys,
        "stats": {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "density": round(nx.density(graph.graph), 4),
            "clustering": round(nx.average_clustering(graph.graph.to_undirected()), 3),
            "has_cycles": has_cycles,
        },
    }
