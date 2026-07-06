import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

BASE = "https://api.openalex.org"
SELECT = "id,title,authorships,publication_year,cited_by_count,referenced_works,abstract_inverted_index,primary_location"
MAILTO = "calybai@research.local"

_rate_lock = threading.Lock()
_last_request = 0.0

def _get(url, params=None, delay=0.1, retries=5):
    global _last_request
    if params is None:
        params = {}
    params["mailto"] = MAILTO
    for attempt in range(retries):
        with _rate_lock:
            now = time.time()
            wait = delay - (now - _last_request)
            if wait > 0:
                time.sleep(wait)
            _last_request = time.time()
            resp = requests.get(url, params=params, timeout=30)
        if resp.status_code in (429, 503, 502, 504):
            backoff = delay * (2 ** attempt) + 0.5
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception(f"Failed after {retries} retries: {url}")

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

def get_citing_works(work_id, limit=50):
    data = _get(f"{BASE}/works", {"filter": f"cites:{work_id}", "per_page": min(limit, 200), "select": SELECT})
    return [_clean_paper(w) for w in data.get("results", [])]

def get_works_batch(ids, delay=0.1):
    result = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        data = _get(f"{BASE}/works", {"filter": "openalex:" + "|".join(chunk), "per_page": 50, "select": SELECT}, delay=delay)
        for w in data.get("results", []):
            result[w["id"]] = _clean_paper(w)
    return result

_STOP = {"the","and","for","with","from","this","that","using","based","paper","study",
          "a","in","to","of","on","by","an","is","we","its","are","it","as","at","their","new"}

def _topic_keywords(query):
    words = query.lower().replace("-", " ").split()
    return list({w for w in words if w not in _STOP and len(w) > 3})

def _is_relevant(title, keywords):
    if not keywords or not title:
        return True
    t = title.lower()
    return any(k in t for k in keywords)

def crawl_topic(query, target=25, cit_limit=0):
    keywords = _topic_keywords(query)
    seeds = search_works(query, limit=50)
    seeds = [p for p in seeds if _is_relevant(p.get("title"), keywords)]
    papers = {}
    edges = []

    for p in seeds:
        papers[p["id"]] = p

    ref_counter = Counter()
    for p in seeds:
        for ref in p.get("referenced_works", []):
            ref_counter[ref] += 1

    max_refs = target * 2 - len(seeds)
    top_refs = [rid for rid, _ in ref_counter.most_common(max_refs) if rid not in papers]

    for rid in top_refs:
        papers[rid] = {"id": rid, "title": None, "year": None, "authors": None, "cited_by_count": 0, "referenced_works": []}

    for p in seeds:
        pid = p["id"]
        for ref in p.get("referenced_works", []):
            if ref in papers:
                edges.append((pid, ref))

    citing_results = []
    if cit_limit > 0:
        seed_sample = list(papers.keys())[:max(target // 2, 20)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            fut_map = {pool.submit(get_citing_works, pid, cit_limit): pid for pid in seed_sample}
            for fut in as_completed(fut_map):
                pid = fut_map[fut]
                try:
                    citing_results.append((pid, fut.result()))
                except Exception:
                    pass

    for pid, citing in citing_results:
        for c in citing:
            if len(papers) >= target * 2:
                break
            if not _is_relevant(c.get("title"), keywords):
                continue
            cid = c["id"]
            if cid not in papers:
                papers[cid] = c
            edges.append((cid, pid))

    ref_ids = [pid for pid, p in papers.items() if p["title"] is None]
    if ref_ids:
        fetched = get_works_batch(ref_ids)
        for rid, rp in fetched.items():
            papers[rid] = rp

    result = [p for p in papers.values() if p["title"] is not None]
    return result, edges
