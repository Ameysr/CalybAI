import networkx as nx

class Curriculum:
    def __init__(self, graph, analyzer):
        self.graph = graph.graph
        self.papers = graph.papers
        self.analyzer = analyzer
        self.stats = analyzer.stats()

    def _resolve_cycles(self):
        try:
            order = list(nx.topological_sort(self.graph))
            return order, False
        except nx.NetworkXUnfeasible:
            pass

        sccs = list(nx.strongly_connected_components(self.graph))
        large_sccs = [s for s in sccs if len(s) > 1]
        condensed = nx.DiGraph()
        scc_map = {}
        for i, scc in enumerate(sccs):
            for n in scc:
                scc_map[n] = i
            condensed.add_node(i)

        for u, v in self.graph.edges():
            if scc_map[u] != scc_map[v]:
                condensed.add_edge(scc_map[u], scc_map[v])

        try:
            condensed_order = list(nx.topological_sort(condensed))
        except nx.NetworkXUnfeasible:
            condensed_order = list(condensed.nodes())

        pr = self.analyzer.pagerank()
        order = []
        for ci in condensed_order:
            scc_nodes = list(sccs[ci])
            if len(scc_nodes) > 1:
                scc_nodes.sort(key=lambda n: pr.get(n, 0), reverse=True)
            order.extend(scc_nodes)

        return order, bool(large_sccs)

    def reading_order(self):
        order, has_cycles = self._resolve_cycles()
        pr = self.analyzer.pagerank()
        in_deg, out_deg = self.analyzer.degree_metrics()

        ordered = []
        for rank, pid in enumerate(order, 1):
            md = self.papers.get(pid, {})
            ordered.append({
                "rank": rank,
                "id": pid,
                "title": md.get("title", "?"),
                "authors": md.get("authors", "?"),
                "year": md.get("year"),
                "citations": md.get("cited_by_count", 0),
                "pagerank": round(pr.get(pid, 0), 6),
                "in_degree": in_deg.get(pid, 0),
                "out_degree": out_deg.get(pid, 0),
            })
        return ordered, has_cycles

    def foundational_papers(self, top_n=10):
        order, _ = self._resolve_cycles()
        pr = self.analyzer.pagerank()
        scored = []
        for rank, pid in enumerate(order):
            score = pr.get(pid, 0) * 1000 - rank * 0.001
            scored.append((score, pid))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for score, pid in scored[:top_n]:
            md = self.papers.get(pid, {})
            result.append({
                "id": pid,
                "title": md.get("title", "?"),
                "authors": md.get("authors", "?"),
                "year": md.get("year"),
                "pagerank": round(pr.get(pid, 0), 6),
            })
        return result

    def survey_papers(self, top_n=5):
        in_deg, out_deg = self.analyzer.degree_metrics()
        scored = [(out_deg.get(pid, 0), pid) for pid in self.graph.nodes()]
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for deg, pid in scored[:top_n]:
            md = self.papers.get(pid, {})
            result.append({
                "id": pid,
                "title": md.get("title", "?"),
                "authors": md.get("authors", "?"),
                "year": md.get("year"),
                "out_degree": deg,
            })
        return result
