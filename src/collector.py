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

    def fetch_all_papers_by_references(self, seed_papers, max_papers=100):
        papers = {}
        refs_to_fetch = []

        for p in seed_papers:
            pid = p["paperId"]
            if pid and pid not in papers:
                papers[pid] = p
                refs_to_fetch.append(pid)

        for pid in refs_to_fetch:
            if len(papers) >= max_papers:
                break
            try:
                refs = self.get_references(pid, limit=20)
                for r in refs:
                    if len(papers) >= max_papers:
                        break
                    rp = r.get("referencedPaper") or r.get("citedPaper")
                    if rp and rp.get("paperId") and rp["paperId"] not in papers:
                        papers[rp["paperId"]] = rp
            except Exception:
                pass

        return list(papers.values())
