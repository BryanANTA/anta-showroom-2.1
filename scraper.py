#!/usr/bin/env python3
"""
ANTA Showroom background enrichment worker.

Design:
- Uses the BFL SA master SKU as authoritative.
- Searches exact SKU and the regional 1<->8 variant.
- Also searches the product name.
- Extracts public product-page metadata and image URLs.
- Does NOT bypass login, CAPTCHAs, robots restrictions, or paywalls.
- Stores source URLs and confidence so results can be reviewed.
- Intended to run in small batches via GitHub Actions.

For production, replace SEARCH_URL_TEMPLATE with a search provider/API that
you are permitted to automate. The fallback HTML search endpoint is deliberately
kept configurable.
"""
import argparse, json, os, re, time, urllib.parse
from pathlib import Path
import requests
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
MASTER=ROOT/"anta_showroom_master.csv"
OUT=ROOT/"enriched_products.json"
HEADERS={"User-Agent":CONFIG["user_agent"],"Accept-Language":"en-US,en;q=0.8"}

# Configurable public search endpoint. Set SEARCH_URL_TEMPLATE in an environment
# variable if your approved search provider has a different URL/API.
SEARCH_URL_TEMPLATE=os.getenv(
    "SEARCH_URL_TEMPLATE",
    "https://html.duckduckgo.com/html/?q={query}"
)

def norm(s):
    return re.sub(r"\s+","",str(s or "").upper())

def variants(sku):
    s=norm(sku)
    vals=[s]
    if len(s)>1 and s[0] in "18":
        vals.append(("1" if s[0]=="8" else "8")+s[1:])
    if "-" in s:
        vals.append(s.replace("-",""))
    return list(dict.fromkeys(vals))

def get(url, timeout=20):
    r=requests.get(url,headers=HEADERS,timeout=timeout)
    r.raise_for_status()
    return r

def search(query):
    url=SEARCH_URL_TEMPLATE.format(query=urllib.parse.quote_plus(query))
    r=get(url)
    soup=BeautifulSoup(r.text,"html.parser")
    results=[]
    for a in soup.select("a.result__a"):
        href=a.get("href","")
        title=a.get_text(" ",strip=True)
        if href and title:
            results.append({"title":title,"url":href})
    return results[:CONFIG["max_pages_per_product"]]

def allowed_by_robots(url):
    # Conservative check. If robots cannot be retrieved, skip rather than bypass.
    from urllib.robotparser import RobotFileParser
    p=urllib.parse.urlparse(url)
    robots=f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        rp=RobotFileParser(robots)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"],url)
    except Exception:
        return False

def extract(url):
    if not allowed_by_robots(url):
        return None
    try:
        r=get(url)
    except Exception:
        return None
    soup=BeautifulSoup(r.text,"html.parser")
    title=(soup.title.get_text(" ",strip=True) if soup.title else "")
    desc=""
    meta=soup.find("meta",attrs={"name":"description"})
    if meta: desc=meta.get("content","").strip()
    # Product JSON-LD
    jsonld=[]
    for tag in soup.find_all("script",type="application/ld+json"):
        try: jsonld.append(json.loads(tag.string or tag.get_text()))
        except Exception: pass
    images=[]
    for img in soup.find_all("img"):
        u=img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not u: continue
        u=urllib.parse.urljoin(url,u)
        if u.startswith("http") and u not in images:
            images.append(u)
    return {
        "url":url, "title":title, "description":desc,
        "images":images[:30], "jsonld":jsonld
    }

def score(record, result):
    hay=(result.get("title","")+" "+result.get("description","")).upper()
    sku=norm(record["sku"])
    alt=norm(record.get("alternate_sku",""))
    name=str(record.get("product_name","")).upper()
    points=0
    if sku and sku in hay: points+=70
    if alt and alt in hay: points+=60
    if name and len(name)>5 and name in hay: points+=25
    # Partial SKU stem is useful but lower confidence.
    for v in variants(sku):
        stem=v.split("-")[0]
        if stem and stem in hay: points+=10
    return min(points,100)

def main(limit):
    df=pd.read_csv(MASTER,dtype=str).fillna("")
    start=0
    if OUT.exists():
        existing=json.loads(OUT.read_text(encoding="utf-8"))
        done={x.get("sku") for x in existing}
    else:
        existing=df.to_dict(orient="records")
        done=set()

    # Work only records not already enriched.
    todo=[i for i,r in df.iterrows() if r["sku"] not in done or not existing]
    todo=todo[:limit]
    output=existing if OUT.exists() else df.to_dict(orient="records")
    bysku={x.get("sku"):x for x in output}

    for n,i in enumerate(todo,1):
        r=df.loc[i].to_dict()
        queries=[]
        for v in variants(r["sku"]): queries.append(f'ANTA "{v}"')
        if r.get("product_name"): queries.append(f'ANTA "{r["product_name"]}" "{r["sku"]}"')
        candidates=[]
        for q in queries:
            try: candidates.extend(search(q))
            except Exception: pass
            time.sleep(CONFIG["delay_seconds"])
        # de-duplicate
        seen=set(); candidates=[x for x in candidates if not (x["url"] in seen or seen.add(x["url"]))]
        best=None
        for c in candidates:
            e=extract(c["url"])
            if not e: continue
            e["match_score"]=score(r,e)
            if best is None or e["match_score"]>best["match_score"]:
                best=e
        rec=bysku[r["sku"]]
        if best:
            rec["web_match_url"]=best["url"]
            rec["web_match_title"]=best["title"]
            rec["web_match_confidence"]=str(best["match_score"])
            rec["web_description"]=best["description"]
            rec["web_images"]=best["images"]
            rec["web_enrichment_status"]="FOUND"
            rec["review_status"]="WEB_MATCH_REVIEW"
        else:
            rec["web_enrichment_status"]="NOT_FOUND"
            rec["review_status"]="NO_WEB_MATCH"
        print(f"{n}/{len(todo)} {r['sku']} -> {rec.get('web_enrichment_status')}")
        OUT.write_text(json.dumps(list(bysku.values()),ensure_ascii=False,indent=2),encoding="utf-8")
    print("Saved",OUT)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit",type=int,default=CONFIG["max_products_per_run"])
    args=ap.parse_args()
    main(args.limit)
