import asyncio
import math
import re
import threading
from collections import Counter
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from src.pipeline import run_pipeline

app = FastAPI(title="CalybAI")

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

cache = {}
cache_lock = threading.RLock()

def _tokenize(text):
    return [w.lower() for w in re.findall(r"\w{3,}", text or "")]

def _tfidf_similarity(query, titles):
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_counts = Counter(q_tokens)
    n = len(titles)
    idf = {}
    for ti, title in titles:
        for w in set(_tokenize(title)):
            idf[w] = idf.get(w, 0) + 1
    results = []
    for ti, title in titles:
        t_counts = Counter(_tokenize(title))
        dot = sum(q_counts[w] * t_counts.get(w, 0) * math.log((n + 1) / (idf.get(w, n) + 1) + 1) for w in q_tokens)
        q_norm = math.sqrt(sum(c * c for c in q_counts.values()))
        t_norm = math.sqrt(sum(c * c for c in t_counts.values()))
        if q_norm * t_norm == 0:
            continue
        results.append((ti, title, round(dot / (q_norm * t_norm), 4)))
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:10]

class RunRequest(BaseModel):
    topic: str
    target: int = 50

def _read_cache():
    with cache_lock:
        if not cache:
            raise HTTPException(404, "Run an analysis first")
        return cache

def _read_cache_field(field):
    return _read_cache()[field]

@app.post("/api/run")
async def run_analysis(req: RunRequest):
    topic = req.topic.strip() if req.topic else ""
    target = max(50, min(200, req.target))

    if not topic:
        raise HTTPException(400, "Topic cannot be empty")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_pipeline, topic, target)

    with cache_lock:
        cache.clear()
        cache.update(result)

    return {"status": "ok", "stats": result["stats"], "topic": result["topic"]}

@app.get("/api/graph")
async def get_graph():
    return _read_cache_field("graph")

@app.get("/api/reading-order")
async def get_reading_order():
    return _read_cache_field("reading_order")

class NoveltyRequest(BaseModel):
    query: str

@app.post("/api/novelty")
async def novelty_check(req: NoveltyRequest):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    nodes = _read_cache_field("graph")["nodes"]
    titles = [(n["id"], n["title"]) for n in nodes if n.get("title")]
    matches = _tfidf_similarity(req.query, titles)
    return {
        "query": req.query,
        "matches": [{"id": mid, "title": mt, "similarity": ms} for mid, mt, ms in matches],
    }

@app.get("/api/foundational")
async def get_foundational():
    return _read_cache_field("foundational")

@app.get("/api/surveys")
async def get_surveys():
    return _read_cache_field("surveys")

@app.get("/api/paper/{pid:path}")
async def get_paper(pid: str):
    for n in _read_cache_field("graph")["nodes"]:
        if n["id"] == pid:
            return n
    raise HTTPException(404, f"Paper not found: {pid}")

@app.get("/api/status")
async def get_status():
    with cache_lock:
        if not cache:
            return {"loaded": False}
        return {"loaded": True, "stats": cache["stats"], "topic": cache["topic"]}

@app.get("/api/trends")
async def get_trends():
    nodes = _read_cache_field("graph")["nodes"]
    by_year = {}
    for n in nodes:
        y = n.get("year")
        if y and n.get("pagerank", 0) > 0:
            by_year.setdefault(y, []).append(n)
    years = sorted(by_year.keys(), reverse=True)
    trends = []
    for y in years[:5]:
        top = sorted(by_year[y], key=lambda n: n["pagerank"], reverse=True)[:3]
        trends.append({
            "year": y,
            "paper_count": len(by_year[y]),
            "top_papers": [{"title": t["title"], "pagerank": t["pagerank"], "citations": t["citations"]} for t in top],
        })
    return {"trends": trends}

@app.get("/api/export.csv")
async def export_csv():
    c = _read_cache()
    lines = ["rank,title,authors,year,citations,pagerank,in_degree,out_degree"]
    for p in c["reading_order"]:
        yr = p.get("year") or ""
        lines.append(f'{p["rank"]},"{p["title"]}","{p["authors"]}",{yr},{p["citations"]},{p["pagerank"]},{p["in_degree"]},{p["out_degree"]}')
    return Response(content="\n".join(lines), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=reading_order.csv"})

@app.get("/api/export.json")
async def export_json():
    c = _read_cache()
    return {
        "topic": c["topic"],
        "stats": c["stats"],
        "reading_order": c["reading_order"],
        "foundational": c["foundational"],
        "surveys": c["surveys"],
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
