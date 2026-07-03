import time
import requests

BASE = "https://api.openalex.org"
SELECT = "id,title,authorships,publication_year,cited_by_count,referenced_works,abstract_inverted_index,primary_location"

def _get(url, params=None, delay=0.1):
    time.sleep(delay)
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def _short_auth(authorships):
    if not authorships:
        return "Unknown"
    names = [a.get("author", {}).get("display_name", "?") for a in authorships[:3]]
    suffix = " et al." if len(authorships) > 3 else ""
    return ", ".join(names) + suffix

def _clean_paper(w):
    return {
        "id": w["id"],
        "title": w.get("title", "Untitled"),
        "year": w.get("publication_year"),
        "authors": _short_auth(w.get("authorships", [])),
        "cited_by_count": w.get("cited_by_count", 0),
        "referenced_works": w.get("referenced_works", []),
    }

def search_works(query, limit=50):
    data = _get(f"{BASE}/works", {"search": query, "per_page": min(limit, 200), "select": SELECT})
    return [_clean_paper(w) for w in data.get("results", [])]

def get_work(work_id):
    w = _get(f"{BASE}/works/{work_id}", {"select": SELECT})
    return _clean_paper(w)

def get_citing_works(work_id, limit=50):
    data = _get(f"{BASE}/works", {"filter": f"cites:{work_id}", "per_page": min(limit, 200), "select": SELECT})
    return [_clean_paper(w) for w in data.get("results", [])]

def get_works_batch(ids, delay=0.05):
    papers = {}
    chunk_size = 50
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i+chunk_size]
        joined = "|".join(chunk)
        data = _get(f"{BASE}/works", {"filter": f"openalex:{joined}", "per_page": chunk_size, "select": SELECT}, delay=delay)
        for w in data.get("results", []):
            papers[w["id"]] = _clean_paper(w)
    return papers

def crawl_topic(query, target=80, ref_limit=50, cit_limit=20):
    papers = {}
    edges = []

    seeds = search_works(query, limit=50)
    for p in seeds:
        papers[p["id"]] = p

    seed_ids = list(papers.keys())
    for i, pid in enumerate(seed_ids):
        if i >= max(target // 2, 20):
            break
        p = papers[pid]
        for ref in p.get("referenced_works", [])[:ref_limit]:
            if len(papers) >= target * 2:
                break
            if ref not in papers:
                papers[ref] = {"id": ref, "title": None, "year": None, "authors": None, "cited_by_count": 0, "referenced_works": []}
            edges.append((pid, ref))

        try:
            citing = get_citing_works(pid, limit=cit_limit)
            for c in citing:
                if len(papers) >= target * 2:
                    break
                cid = c["id"]
                if cid not in papers:
                    papers[cid] = c
                edges.append((cid, pid))
        except Exception:
            pass

    ref_ids = [pid for pid, p in papers.items() if p["title"] is None]
    if ref_ids:
        fetched = get_works_batch(ref_ids)
        for rid, rp in fetched.items():
            papers[rid] = rp

    result = [p for p in papers.values() if p["title"] is not None]
    return result, edges
