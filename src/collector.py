import time
import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,abstract,citationCount,referenceCount,externalIds,url,publicationTypes,influentialCitationCount"

class Collector:
    def __init__(self, delay=1.0):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CalybAI/1.0"})
        self.delay = delay

    def _get(self, url, params=None):
        time.sleep(self.delay)
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_papers(self, query, limit=50):
        data = self._get(f"{BASE_URL}/paper/search", {"query": query, "limit": min(limit, 100), "fields": FIELDS})
        return data.get("data", [])

    def get_paper(self, paper_id):
        return self._get(f"{BASE_URL}/paper/{paper_id}", {"fields": FIELDS})

    def get_references(self, paper_id, limit=50):
        data = self._get(f"{BASE_URL}/paper/{paper_id}/references", {"limit": min(limit, 100), "fields": FIELDS})
        return data.get("data", [])

    def get_citations(self, paper_id, limit=50):
        data = self._get(f"{BASE_URL}/paper/{paper_id}/citations", {"limit": min(limit, 100), "fields": FIELDS})
        return data.get("data", [])

    def crawl_topic(self, query, target=80, ref_limit=30, cit_limit=20):
        papers = {}
        edges = []

        seeds = self.search_papers(query, limit=min(target, 100))
        for p in seeds:
            pid = p["paperId"]
            if pid not in papers:
                papers[pid] = p

        pids = list(papers.keys())
        for pid in pids:
            if len(papers) >= target:
                break
            try:
                refs = self.get_references(pid, limit=ref_limit)
                for r in refs:
                    if len(papers) >= target:
                        break
                    rp = r.get("referencedPaper")
                    if rp and rp.get("paperId"):
                        rid = rp["paperId"]
                        if rid not in papers:
                            papers[rid] = rp
                        edges.append((pid, rid))
            except Exception:
                pass

            try:
                cites = self.get_citations(pid, limit=cit_limit)
                for c in cites:
                    if len(papers) >= target:
                        break
                    cp = c.get("citingPaper")
                    if cp and cp.get("paperId"):
                        cid = cp["paperId"]
                        if cid not in papers:
                            papers[cid] = cp
                        edges.append((cid, pid))
            except Exception:
                pass

        return list(papers.values()), edges
