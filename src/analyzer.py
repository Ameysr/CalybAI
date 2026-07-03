import networkx as nx

class Analyzer:
    def __init__(self, graph):
        self.graph = graph.graph
        self.papers = graph.papers

    def pagerank(self):
        return nx.pagerank(self.graph, alpha=0.85)

    def degree_metrics(self):
        in_deg = dict(self.graph.in_degree())
        out_deg = dict(self.graph.out_degree())
        return in_deg, out_deg

    def betweenness(self):
        undirected = self.graph.to_undirected()
        if undirected.number_of_nodes() > 500:
            return {}
        return nx.betweenness_centrality(undirected, k=min(100, undirected.number_of_nodes()))

    def detect_communities(self):
        try:
            import community as community_louvain
            undirected = self.graph.to_undirected()
            partition = community_louvain.best_partition(undirected)
            return partition
        except ImportError:
            comps = list(nx.algorithms.community.greedy_modularity_communities(self.graph.to_undirected()))
            return {n: i for i, c in enumerate(comps) for n in c}

    def stats(self):
        pr = self.pagerank()
        in_deg, out_deg = self.degree_metrics()
        bc = self.betweenness()

        rows = []
        for pid, md in self.papers.items():
            rows.append({
                "id": pid,
                "title": md.get("title", "?"),
                "authors": md.get("authors", "?"),
                "year": md.get("year"),
                "citations": md.get("cited_by_count", 0),
                "pagerank": round(pr.get(pid, 0), 6),
                "in_degree": in_deg.get(pid, 0),
                "out_degree": out_deg.get(pid, 0),
                "betweenness": round(bc.get(pid, 0), 6),
            })
        return rows
