import networkx as nx

class Analyzer:
    def __init__(self, graph):
        self.graph = graph.graph
        self.papers = graph.papers
        self._pagerank = None
        self._in_deg = None
        self._out_deg = None
        self._betweenness = None
        self._communities = None

    def pagerank(self):
        if self._pagerank is None:
            self._pagerank = nx.pagerank(self.graph, alpha=0.85)
        return self._pagerank

    def degree_metrics(self):
        if self._in_deg is None:
            self._in_deg = dict(self.graph.in_degree())
            self._out_deg = dict(self.graph.out_degree())
        return self._in_deg, self._out_deg

    def betweenness(self):
        if self._betweenness is None:
            undirected = self.graph.to_undirected()
            if undirected.number_of_nodes() > 500:
                self._betweenness = {}
            else:
                self._betweenness = nx.betweenness_centrality(undirected, k=min(100, undirected.number_of_nodes()))
        return self._betweenness

    def detect_communities(self):
        if self._communities is not None:
            return self._communities
        try:
            import community as community_louvain
            undirected = self.graph.to_undirected()
            self._communities = community_louvain.best_partition(undirected)
        except ImportError:
            comps = list(nx.algorithms.community.greedy_modularity_communities(self.graph.to_undirected()))
            self._communities = {n: i for i, c in enumerate(comps) for n in c}
        return self._communities

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
