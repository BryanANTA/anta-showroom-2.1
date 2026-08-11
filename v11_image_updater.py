#!/usr/bin/env python3
import argparse,csv,json,os,re,time,urllib.parse
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"v11_config.json").read_text())
PRODUCTS=ROOT/"products.json"
REVIEW=ROOT/"review_queue_v11.csv"
HEADERS={"User-Agent":CFG["user_agent"],"Accept-Language":"en-US,en;q=0.8"}
SEARCH_TEMPLATE=os.getenv("SEARCH_URL_TEMPLATE","https://html.duckduckgo.com/html/?q={query}")

def norm(s): return re.sub(r"\s+","",str(s or "").upper())
def variants(sku):
    s=norm(sku); out=[s]
    if len(s)>1 and s[0] in "18": out.append(("1" if s[0]=="8" else "8")+s[1:])
    if "-" in s: out.append(s.replace("-",""))
    return list(dict.fromkeys(out))

def allowed(url):
    try:
        p=urllib.parse.urlparse(url)
        rp=RobotFileParser(f"{p.scheme}://{p.netloc}/robots.txt"); rp.read()
        return rp.can_fetch(HEADERS["User-Agent"],url)
    except: return False

def get(url):
    r=requests.get(url,headers=HEADERS,timeout=20); r.raise_for_status(); return r

def search(q):
    try: soup=BeautifulSoup(get(SEARCH_TEMPLATE.format(query=urllib.parse.quote_plus(q))).text,"html.parser")
    except: return []
    out=[]
    for a in soup.select("a.result__a"):
        if a.get("href"): out.append({"url":a["href"],"title":a.get_text(" ",strip=True)})
        if len(out)>=CFG["max_search_results"]: break
    return out

def extract(url):
    if not allowed(url): return None
    try: soup=BeautifulSoup(get(url).text,"html.parser")
    except: return None
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    desc=""
    m=soup.find("meta",attrs={"name":"description"})
    if m: desc=m.get("content","").strip()
    imgs=[]
    for sel,attr in [('meta[property="og:image"]',"content"),('meta[name="twitter:image"]',"content")]:
        for t in soup.select(sel):
            u=t.get(attr,"")
            if u:
                u=urllib.parse.urljoin(url,u)
                if u.startswith("http") and u not in imgs: imgs.append(u)
    for img in soup.find_all("img"):
        u=img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if u:
            u=urllib.parse.urljoin(url,u)
            if u.startswith("http") and u not in imgs: imgs.append(u)
    return {"url":url,"title":title,"description":desc,"images":imgs[:30]}

def score(p,page):
    hay=(page["title"]+" "+page["description"]).upper()
    s=0
    sku=norm(p.get("sku")); alt=norm(p.get("alternate_sku")); name=str(p.get("product_name","")).upper()
    if sku and sku in hay: s+=70
    if alt and alt in hay: s+=62
    for v in variants(sku):
        stem=v.split("-")[0]
        if stem and stem in hay: s+=10; break
    if name and len(name)>=4 and name in hay: s+=20
    if len(page["images"])>=2: s+=5
    return min(100,s)

def review_row(p,best):
    exists=REVIEW.exists()
    with REVIEW.open("a",newline="",encoding="utf-8-sig") as f:
        cols=["sku","alternate_sku","product_name","candidate_url","candidate_title","confidence","image_count","status"]
        w=csv.DictWriter(f,fieldnames=cols)
        if not exists: w.writeheader()
        w.writerow({"sku":p.get("sku",""),"alternate_sku":p.get("alternate_sku",""),"product_name":p.get("product_name",""),
                    "candidate_url":best["url"],"candidate_title":best["title"],"confidence":best["confidence"],
                    "image_count":len(best["images"]),"status":"PENDING"})

def enrich(p):
    qs=[]
    for v in variants(p.get("sku","")): qs.append(f'ANTA "{v}"')
    if p.get("product_name"): qs.append(f'ANTA "{p["product_name"]}" "{p["sku"]}"')
    cand={}
    for q in qs:
        for r in search(q): cand.setdefault(r["url"],r)
        time.sleep(CFG["delay_seconds"])
    best=None
    for c in list(cand.values())[:16]:
        page=extract(c["url"])
        if not page: continue
        page["confidence"]=score(p,page)
        if best is None or page["confidence"]>best["confidence"]: best=page
    if not best:
        p["image_status"]="NOT_FOUND"; return p
    p["web_match_url"]=best["url"]; p["web_match_title"]=best["title"]; p["web_match_confidence"]=str(best["confidence"])
    conf=best["confidence"]; imgs=best["images"][:CFG["max_images_per_product"]]
    if conf>=CFG["auto_publish_threshold"] and imgs:
        for i in range(1,7): p[f"image_{i}_url"]=imgs[i-1] if i<=len(imgs) else ""
        p["image_source"]=best["url"]; p["image_confidence"]=str(conf); p["image_status"]="AUTO_PUBLISHED"; p["review_status"]="AUTO_APPROVED"
    elif conf>=CFG["review_threshold"]:
        p["image_status"]="REVIEW_REQUIRED"; p["review_status"]="WEB_MATCH_REVIEW"; review_row(p,best)
    else:
        p["image_status"]="LOW_CONFIDENCE"; p["review_status"]="LOW_CONFIDENCE"
    return p

def main(limit):
    products=json.loads(PRODUCTS.read_text(encoding="utf-8"))
    todo=[i for i,p in enumerate(products) if not p.get("image_1_url")][:limit]
    for n,i in enumerate(todo,1):
        print(f"{n}/{len(todo)} {products[i].get('sku')}")
        products[i]=enrich(products[i])
        PRODUCTS.write_text(json.dumps(products,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Processed",len(todo))

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=10)
    args=ap.parse_args(); main(args.limit)
