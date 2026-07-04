import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))
from pipeline import run_pipeline

app = FastAPI(title="CalybAI")

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

cache = {}
cache_lock = threading.Lock()

class RunRequest(BaseModel):
    topic: str
    target: int = 80

def _get_cache():
    with cache_lock:
        if not cache:
            raise HTTPException(404, "Run an analysis first")
        return cache

@app.post("/api/run")
async def run_analysis(req: RunRequest):
    with cache_lock:
        result = run_pipeline(req.topic, req.target)
        cache.clear()
        cache.update(result)
        return {"status": "ok", "stats": result["stats"], "topic": result["topic"]}

@app.get("/api/graph")
async def get_graph():
    return _get_cache()["graph"]

@app.get("/api/reading-order")
async def get_reading_order():
    return _get_cache()["reading_order"]

@app.get("/api/foundational")
async def get_foundational():
    return _get_cache()["foundational"]

@app.get("/api/surveys")
async def get_surveys():
    return _get_cache()["surveys"]

@app.get("/api/paper/{pid:path}")
async def get_paper(pid: str):
    for n in _get_cache()["graph"]["nodes"]:
        if n["id"] == pid:
            return n
    raise HTTPException(404, f"Paper not found: {pid}")

@app.get("/api/status")
async def get_status():
    with cache_lock:
        if not cache:
            return {"loaded": False}
        return {"loaded": True, "stats": cache["stats"], "topic": cache["topic"]}

@app.get("/api/export.csv")
async def export_csv():
    c = _get_cache()
    lines = ["rank,title,authors,year,citations,pagerank,in_degree,out_degree"]
    for p in c["reading_order"]:
        yr = p.get("year") or ""
        lines.append(f'{p["rank"]},"{p["title"]}","{p["authors"]}",{yr},{p["citations"]},{p["pagerank"]},{p["in_degree"]},{p["out_degree"]}')
    return Response(content="\n".join(lines), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=reading_order.csv"})

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
