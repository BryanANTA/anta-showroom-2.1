#!/usr/bin/env python3
import argparse,csv,io,json,re,urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image
from ddgs import DDGS

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"v11_2_config.json").read_text())
PRODUCTS=ROOT/"products.json"
LOG=ROOT/"v11_2_last_run.json"
REVIEW=ROOT/"review_queue_v11_2.csv"
HEAD={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
      "Accept-Language":"en-US,en;q=0.8"}

def norm(s): return re.sub(r"\s+","",str(s or "").upper())

def variants(sku):
    s=norm(sku); out=[s]
    if len(s)>1 and s[0] in "18":
        out.append(("1" if s[0]=="8" else "8")+s[1:])
    if "-" in s:
        out.append(s.replace("-",""))
    return list(dict.fromkeys(out))

def sku_stems(sku):
    out=[]
    for v in variants(sku):
        out += [v, v.replace("-",""), v.split("-")[0]]
    return list(dict.fromkeys([x for x in out if x]))

def name_tokens(name):
    return [x for x in re.split(r"[^A-Z0-9]+",str(name or "").upper()) if len(x)>=3]

def generic_page(url,title):
    u=(url or "").lower()
    t=(title or "").lower()
    if any(x in u for x in CFG["reject_path_terms"]): return True
    generic=["collection","all shoes","sports collection","search results","category"]
    return any(x in t for x in generic)

def get(url):
    r=requests.get(url,headers=HEAD,timeout=CFG["request_timeout"])
    r.raise_for_status()
    return r

def validate_image(url):
    try:
        r=get(url)
        if not r.headers.get("content-type","").lower().startswith("image/"): return False,0,0
        im=Image.open(io.BytesIO(r.content))
        w,h=im.size
        return w>=CFG["image_min_width"] and h>=CFG["image_min_height"],w,h
    except: return False,0,0

def extract_product_page(url):
    try:
        r=get(url)
    except:
        return None
    soup=BeautifulSoup(r.text,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    text=soup.get_text(" ",strip=True)
    imgs=[]

    for sel,attr in [
        ('meta[property="og:image"]',"content"),
        ('meta[name="twitter:image"]',"content"),
        ('meta[itemprop="image"]',"content")
    ]:
        for tag in soup.select(sel):
            u=tag.get(attr,"")
            if u:
                u=urllib.parse.urljoin(url,u)
                if u.startswith("http") and u not in imgs: imgs.append(u)

    for tag in soup.find_all("script",type="application/ld+json"):
        try:
            data=json.loads(tag.string or tag.get_text())
        except:
            continue
        blocks=data if isinstance(data,list) else [data]
        for b in blocks:
            if not isinstance(b,dict): continue
            typ=b.get("@type")
            if isinstance(typ,list): isprod="Product" in typ
            else: isprod=typ=="Product"
            if not isprod: continue
            image=b.get("image")
            if isinstance(image,str): image=[image]
            if isinstance(image,list):
                for u in image:
                    if isinstance(u,str):
                        u=urllib.parse.urljoin(url,u)
                        if u.startswith("http") and u not in imgs: imgs.append(u)

    for img in soup.find_all("img"):
        u=img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if u:
            u=urllib.parse.urljoin(url,u)
            if u.startswith("http") and u not in imgs: imgs.append(u)

    return {"url":url,"title":title,"text":text[:100000],"images":imgs[:40]}

def page_score(p,page):
    if generic_page(page["url"],page["title"]): return 0
    hay=(page["title"]+" "+page["url"]+" "+page["text"]).upper()
    sku=norm(p.get("sku")); alt=norm(p.get("alternate_sku")); name=p.get("product_name","")
    score=0

    exact=False
    if sku and sku in hay:
        score+=75; exact=True
    if alt and alt in hay:
        score+=68; exact=True

    if not exact:
        for st in sku_stems(sku):
            if st and st in hay:
                score+=24
                break

    toks=name_tokens(name)
    if toks:
        hits=sum(1 for t in toks if t in hay)
        score+=min(20,int(20*hits/len(toks)))

    host=urllib.parse.urlparse(page["url"]).netloc.lower()
    if any(d.lower() in host for d in CFG["preferred_domains"]):
        score+=6

    if "/product" in page["url"].lower() or "/item" in page["url"].lower() or "/p/" in page["url"].lower():
        score+=5

    if len(page["images"])>=3: score+=5
    return min(100,score)

def search_pages(p):
    sku=p.get("sku",""); name=p.get("product_name","")
    queries=[]
    for v in variants(sku):
        queries += [
            f'"{v}" ANTA',
            f'"{v}" ANTA product',
            f'"{v}" shoe',
            f'site:anta.com "{v}"'
        ]
    for st in sku_stems(sku):
        queries += [f'"{st}" ANTA']
    if name:
        queries += [f'ANTA "{name}" "{sku}"', f'ANTA "{name}" product']

    ddgs=DDGS(); results=[]; seen=set()
    for q in dict.fromkeys(queries):
        try:
            for r in ddgs.text(q,max_results=CFG["max_web_results"]):
                url=r.get("href") or r.get("url") or ""
                title=r.get("title") or ""
                if not url or url in seen: continue
                seen.add(url)
                if generic_page(url,title): continue
                results.append({"url":url,"title":title,"query":q})
        except:
            pass
    return results

def enrich(p):
    page_results=search_pages(p)
    checked=[]
    best=None

    for r in page_results:
        page=extract_product_page(r["url"])
        if not page: continue
        sc=page_score(p,page)
        checked.append({"url":page["url"],"title":page["title"],"score":sc,"images":len(page["images"])})
        if sc<=0: continue
        page["score"]=sc
        if best is None or sc>best["score"]:
            best=page

    if not best:
        p["image_status"]="NOT_FOUND"; p["review_status"]="NO_PRODUCT_PAGE"
        return p,{"sku":p.get("sku"),"status":"NOT_FOUND","score":0,"source":"","title":"","images":0,"pages_checked":len(checked)}

    valid=[]
    for u in best["images"]:
        ok,w,h=validate_image(u)
        if ok:
            valid.append({"url":u,"width":w,"height":h})
        if len(valid)>=CFG["max_images_per_product"]: break

    if best["score"]>=CFG["auto_publish_threshold"] and valid:
        for i in range(1,7):
            p[f"image_{i}_url"]=valid[i-1]["url"] if i<=len(valid) else ""
        p["image_source"]=best["url"]; p["image_confidence"]=str(best["score"]); p["image_status"]="AUTO_PUBLISHED"
        p["review_status"]="AUTO_APPROVED"
        status="AUTO_PUBLISHED"
    elif best["score"]>=CFG["review_threshold"]:
        p["image_status"]="REVIEW_REQUIRED"; p["review_status"]="WEB_MATCH_REVIEW"
        status="REVIEW_REQUIRED"
        new=not REVIEW.exists()
        with REVIEW.open("a",newline="",encoding="utf-8-sig") as f:
            cols=["sku","product_name","candidate_url","candidate_title","confidence","valid_images","status"]
            w=csv.DictWriter(f,fieldnames=cols)
            if new: w.writeheader()
            w.writerow({"sku":p.get("sku"),"product_name":p.get("product_name"),"candidate_url":best["url"],
                        "candidate_title":best["title"],"confidence":best["score"],"valid_images":len(valid),"status":"PENDING"})
    else:
        p["image_status"]="LOW_CONFIDENCE"; p["review_status"]="LOW_CONFIDENCE"
        status="LOW_CONFIDENCE"

    p["web_match_url"]=best["url"]; p["web_match_title"]=best["title"]; p["web_match_confidence"]=str(best["score"])
    return p,{"sku":p.get("sku"),"status":status,"score":best["score"],"source":best["url"],
              "title":best["title"],"images":len(valid),"pages_checked":len(checked)}

def main(limit,skus):
    products=json.loads(PRODUCTS.read_text())
    wanted={norm(x) for x in skus if x.strip()}
    idx=[]
    for i,p in enumerate(products):
        if wanted:
            if norm(p.get("sku")) in wanted or norm(p.get("alternate_sku")) in wanted: idx.append(i)
        elif not p.get("image_1_url"):
            idx.append(i)
        if len(idx)>=limit: break

    out=[]
    for n,i in enumerate(idx,1):
        p=products[i]
        print(f"{n}/{len(idx)} {p.get('sku')} | {p.get('product_name','')}")
        products[i],diag=enrich(p); out.append(diag)
        print(f" -> {diag['status']} score={diag['score']} images={diag['images']} source={diag['source']}")
    PRODUCTS.write_text(json.dumps(products,ensure_ascii=False,indent=2))
    LOG.write_text(json.dumps(out,ensure_ascii=False,indent=2))

    print("SUMMARY")
    for x in out:
        print(x["sku"],x["status"],x["score"],x["images"],x["title"])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit",type=int,default=5)
    ap.add_argument("--sku",action="append",default=[])
    a=ap.parse_args()
    main(a.limit,a.sku)
