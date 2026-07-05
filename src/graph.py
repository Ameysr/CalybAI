import json
import networkx as nx
from pathlib import Path

def paper_label(p):
    year = p.get("year", "?")
    authors = p.get("authors", "Unknown")
    title = (p.get("title") or "Untitled")[:60]
    return f"[{year}] {authors}: {title}"

class PaperGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.papers = {}

    def add_paper(self, paper_id, metadata):
        if paper_id not in self.papers:
            self.papers[paper_id] = metadata
            label = paper_label(metadata)
            year = metadata.get("year", 0) or 0
            self.graph.add_node(paper_id, label=label, year=year)

    def add_citation(self, from_id, to_id):
        if from_id in self.graph and to_id in self.graph:
            self.graph.add_edge(from_id, to_id)

    def from_collector(self, query, target=25):
        from collector import crawl_topic
        papers_list, edges = crawl_topic(query, target=target)
        for p in papers_list:
            self.add_paper(p["id"], p)
        for fr, to in edges:
            self.add_citation(fr, to)
        return self

    def largest_component(self):
        if self.graph.number_of_nodes() == 0:
            return self
        undirected = self.graph.to_undirected()
        comps = list(nx.connected_components(undirected))
        if not comps:
            return self
        largest = max(comps, key=len)
        sub = self.graph.subgraph(largest).copy()
        new = PaperGraph()
        new.graph = sub
        new.papers = {pid: self.papers[pid] for pid in sub.nodes()}
        return new

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "papers": {pid: p for pid, p in self.papers.items()},
            "edges": [(u, v) for u, v in self.graph.edges()],
        }
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        pg = cls()
        for pid, p in data["papers"].items():
            pg.add_paper(pid, p)
        for u, v in data["edges"]:
            if u in pg.graph and v in pg.graph:
                pg.graph.add_edge(u, v)
        return pg

    @property
    def node_count(self):
        return self.graph.number_of_nodes()

    @property
    def edge_count(self):
        return self.graph.number_of_edges()
