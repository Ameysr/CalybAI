import requests

resp = requests.get("https://api.openalex.org/works?search=retrieval augmented generation&per_page=10", timeout=30)
for w in resp.json()["results"]:
    rid = w["id"]
    yr = w["publication_year"]
    rc = w["referenced_works_count"]
    cc = w["cited_by_count"]
    title = w["title"][:80]
    print(f"{rid} | {yr} | {rc} refs | {cc} cites | {title}")
    if rc > 0:
        print(f"  Sample refs: {w['referenced_works'][:3]}")
