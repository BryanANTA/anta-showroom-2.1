#!/usr/bin/env python3
import argparse,csv,io,json,re,urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from PIL import Image
from ddgs import DDGS

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"v12_config.json").read_text())
PRODUCTS=ROOT/"products.json"
LOG=ROOT/"v12_last_run.json"
REVIEW=ROOT/"review_queue_v12.csv"
HEAD={"User-Agent":"Mozilla/5.0","Accept-Language":"en-US,en;q=0.8"}

def norm(s): return re.sub(r"\s+","",str(s or "").upper())

def variants(s):
    s=norm(s); out=[s]
    if len(s)>1 and s[0] in "18": out.append(("1" if s[0]=="8" else "8")+s[1:])
    if "-" in s: out.append(s.replace("-",""))
    return list(dict.fromkeys(out))

def stems(s):
    out=[]
    for v in variants(s): out += [v,v.replace("-",""),v.split("-")[0]]
    return list(dict.fromkeys([x for x in out if x]))

def generic(url,title):
    u=(url or "").lower(); t=(title or "").lower()
    if any(x in u for x in CFG["reject_path_terms"]): return True
    return any(x in t for x in ["collection","all shoes","search results","category"])

def get(url):
    r=requests.get(url,headers=HEAD,timeout=CFG["request_timeout"]); r.raise_for_status(); return r

def clean(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()[:CFG["description_max_chars"]]

def extract(url):
    try: soup=BeautifulSoup(get(url).text,"html.parser")
    except: return None
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    meta=""
    for attrs in [{"name":"description"},{"property":"og:description"}]:
        m=soup.find("meta",attrs=attrs)
        if m and m.get("content"):
            meta=clean(m.get("content"))
            if len(meta)>=CFG["description_min_chars"]: break
    product_desc=""; features=[]; imgs=[]
    for tag in soup.find_all("script",type="application/ld+json"):
        try: data=json.loads(tag.string or tag.get_text())
        except: continue
        stack=data if isinstance(data,list) else [data]
        for obj in stack:
            if isinstance(obj,dict) and obj.get("@type")=="Product":
                product_desc=clean(obj.get("description","")) or product_desc
                im=obj.get("image")
                if isinstance(im,str): im=[im]
                if isinstance(im,list):
                    for u in im:
                        if isinstance(u,str):
                            u=urllib.parse.urljoin(url,u)
                            if u.startswith("http") and u not in imgs: imgs.append(u)
                ap=obj.get("additionalProperty")
                if isinstance(ap,list):
                    for x in ap:
                        if isinstance(x,dict) and x.get("name") and x.get("value"):
                            features.append(f"{x['name']}: {x['value']}")
    for sel,attr in [('meta[property="og:image"]',"content"),('meta[name="twitter:image"]',"content")]:
        for tag in soup.select(sel):
            u=tag.get(attr,"")
            if u:
                u=urllib.parse.urljoin(url,u)
                if u.startswith("http") and u not in imgs: imgs.append(u)
    text=clean(soup.get_text(" ",strip=True))
    return {"url":url,"title":title,"text":text,"description":product_desc or meta,"features":features[:10],"images":imgs[:30]}

def page_score(p,page):
    if generic(page["url"],page["title"]): return 0
    hay=(page["title"]+" "+page["url"]+" "+page["text"]).upper()
    score=0; sku=norm(p.get("sku")); alt=norm(p.get("alternate_sku")); name=str(p.get("product_name","")).upper()
    if sku and sku in hay: score+=75
    elif alt and alt in hay: score+=68
    else:
        for st in stems(sku):
            if st and st in hay: score+=24; break
    toks=[x for x in re.split(r"[^A-Z0-9]+",name) if len(x)>=3]
    if toks:
        hits=sum(1 for t in toks if t in hay); score+=min(20,int(20*hits/len(toks)))
    if len(page["images"])>=3: score+=4
    if len(page["description"])>=CFG["description_min_chars"]: score+=5
    return min(100,score)

def validate_image(url):
    try:
        r=get(url)
        if not r.headers.get("content-type","").lower().startswith("image/"): return False
        im=Image.open(io.BytesIO(r.content))
        return im.width>=CFG["image_min_width"] and im.height>=CFG["image_min_height"]
    except: return False

def search_pages(p):
    q=[]
    sku=p.get("sku",""); name=p.get("product_name","")
    for v in variants(sku):
        q += [f'"{v}" ANTA',f'"{v}" ANTA product',f'"{v}" shoe']
    for st in stems(sku): q.append(f'"{st}" ANTA')
    if name: q += [f'ANTA "{name}" "{sku}"',f'ANTA "{name}" product description']
    d=DDGS(); out=[]; seen=set()
    for query in dict.fromkeys(q):
        try:
            for r in d.text(query,max_results=CFG["max_web_results"]):
                url=r.get("href") or r.get("url") or ""; title=r.get("title") or ""
                if not url or url in seen or generic(url,title): continue
                seen.add(url); out.append(url)
        except: pass
    return out

def enrich(p):
    best=None
    for url in search_pages(p):
        page=extract(url)
        if not page: continue
        sc=page_score(p,page)
        if sc and (best is None or sc>best["score"]):
            page["score"]=sc; best=page
    if not best:
        p["image_status"]="NOT_FOUND"; p["description_enrichment_status"]="NOT_FOUND"; return p,0,"","NOT_FOUND","NOT_FOUND"
    valid=[u for u in best["images"] if validate_image(u)][:CFG["max_images_per_product"]]
    image_status="NOT_FOUND"; desc_status="NOT_FOUND"
    if best["score"]>=CFG["auto_publish_image_threshold"] and valid:
        for i in range(1,7): p[f"image_{i}_url"]=valid[i-1] if i<=len(valid) else ""
        p["image_source"]=best["url"]; p["image_confidence"]=str(best["score"]); image_status="AUTO_PUBLISHED"
    elif best["score"]>=CFG["review_threshold"] and valid: image_status="REVIEW_REQUIRED"
    desc=best["description"]
    if len(desc)>=CFG["description_min_chars"]:
        p["scraped_description_candidate"]=desc
        p["scraped_features_candidate"]=" • ".join(best["features"])
        p["description_source_url"]=best["url"]
        p["description_confidence"]=str(best["score"])
        if best["score"]>=CFG["auto_publish_description_threshold"]:
            p["listing_description"]=desc; p["listing_features"]=" • ".join(best["features"]); desc_status="AUTO_PUBLISHED"
        elif best["score"]>=CFG["review_threshold"]: desc_status="REVIEW_REQUIRED"
    p["image_status"]=image_status; p["description_enrichment_status"]=desc_status
    p["web_match_url"]=best["url"]; p["web_match_title"]=best["title"]; p["web_match_confidence"]=str(best["score"])
    return p,best["score"],best["url"],image_status,desc_status

def main(limit,skus):
    products=json.loads(PRODUCTS.read_text())
    wanted={norm(x) for x in skus if x.strip()}
    idx=[]
    for i,p in enumerate(products):
        if wanted:
            if norm(p.get("sku")) in wanted or norm(p.get("alternate_sku")) in wanted: idx.append(i)
        elif not p.get("image_1_url") or not p.get("listing_description"):
            idx.append(i)
        if len(idx)>=limit: break
    out=[]
    for n,i in enumerate(idx,1):
        products[i],sc,src,ims,ds=enrich(products[i])
        print(f"{n}/{len(idx)} {products[i].get('sku')} score={sc} image={ims} description={ds} source={src}")
        out.append({"sku":products[i].get("sku"),"score":sc,"source":src,"image_status":ims,"description_status":ds})
    PRODUCTS.write_text(json.dumps(products,ensure_ascii=False,indent=2))
    LOG.write_text(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit",type=int,default=5)
    ap.add_argument("--sku",action="append",default=[])
    a=ap.parse_args(); main(a.limit,a.sku)
