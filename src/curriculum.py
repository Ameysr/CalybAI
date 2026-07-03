import networkx as nx

class Curriculum:
    def __init__(self, graph, analyzer):
        self.graph = graph.graph
        self.papers = graph.papers
        self.analyzer = analyzer

    def _resolve_order(self):
        pr = self.analyzer.pagerank()

        try:
            ts_order = list(nx.topological_sort(self.graph))
            has_cycles = False
        except nx.NetworkXUnfeasible:
            sccs = list(nx.strongly_connected_components(self.graph))
            scc_map = {}
            for i, scc in enumerate(sccs):
                for n in scc:
                    scc_map[n] = i
            condensed = nx.DiGraph()
            for i in range(len(sccs)):
                condensed.add_node(i)
            for u, v in self.graph.edges():
                if scc_map[u] != scc_map[v]:
                    condensed.add_edge(scc_map[u], scc_map[v])
            try:
                corder = list(nx.topological_sort(condensed))
            except nx.NetworkXUnfeasible:
                corder = list(condensed.nodes())
            ts_order = []
            for ci in corder:
                nodes = sorted(sccs[ci], key=lambda n: pr.get(n, 0), reverse=True)
                ts_order.extend(nodes)
            has_cycles = True

        ts_index = {pid: i for i, pid in enumerate(ts_order)}

        depths = {}
        for pid in ts_order:
            preds = list(self.graph.predecessors(pid))
            if not preds:
                depths[pid] = 0
            else:
                depths[pid] = 1 + max(depths.get(p, -1) for p in preds)

        return ts_order, depths, has_cycles

    def reading_order(self):
        pr = self.analyzer.pagerank()
        in_deg, out_deg = self.analyzer.degree_metrics()
        ts_order, depths, has_cycles = self._resolve_order()

        nodes = list(self.graph.nodes())
        nodes.sort(key=lambda pid: (
            depths.get(pid, 0),
            self.papers.get(pid, {}).get("year") or 9999,
            -pr.get(pid, 0),
            -in_deg.get(pid, 0)
        ))

        result = []
        for rank, pid in enumerate(nodes, 1):
            md = self.papers.get(pid, {})
            result.append({
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
        return result, has_cycles

    def foundational_papers(self, top_n=10):
        order, _ = self.reading_order()
        order_map = {p["id"]: p["rank"] for p in order}
        pr = self.analyzer.pagerank()
        scored = []
        for pid in self.graph.nodes():
            rank = order_map.get(pid, 9999)
            score = pr.get(pid, 0) - rank * 0.0001
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
        out_deg = dict(self.graph.out_degree())
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
