#!/usr/bin/env python3
import argparse,csv,io,json,re,urllib.parse
from pathlib import Path
import requests
from PIL import Image
from ddgs import DDGS

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"v11_1_config.json").read_text())
PRODUCTS=ROOT/"products.json"
LOG=ROOT/"v11_1_last_run.json"
REVIEW=ROOT/"review_queue_v11_1.csv"
HEAD={"User-Agent":"Mozilla/5.0","Accept-Language":"en-US,en;q=0.8"}

def norm(s): return re.sub(r"\s+","",str(s or "").upper())
def variants(s):
    s=norm(s); out=[s]
    if len(s)>1 and s[0] in "18": out.append(("1" if s[0]=="8" else "8")+s[1:])
    if "-" in s: out.append(s.replace("-",""))
    return list(dict.fromkeys(out))

def tokens(name):
    return [x for x in re.split(r"[^A-Z0-9]+",str(name or "").upper()) if len(x)>=3]

def score(p,title,source):
    hay=(str(title)+" "+str(source)).upper()
    sc=0
    sku=norm(p.get("sku")); alt=norm(p.get("alternate_sku"))
    if sku and sku in hay: sc+=65
    if alt and alt in hay: sc+=58
    for v in variants(sku):
        st=v.split("-")[0]
        if st and st in hay: sc+=12; break
    ts=tokens(p.get("product_name"))
    if ts:
        hits=sum(t in hay for t in ts)
        sc+=min(18,int(18*hits/len(ts)))
    return min(100,sc)

def image_ok(url):
    try:
        r=requests.get(url,headers=HEAD,timeout=CFG["request_timeout"])
        r.raise_for_status()
        if not r.headers.get("content-type","").lower().startswith("image/"): return False,0,0
        im=Image.open(io.BytesIO(r.content))
        w,h=im.size
        return w>=CFG["image_min_width"] and h>=CFG["image_min_height"],w,h
    except: return False,0,0

def enrich(p):
    qs=[]
    for v in variants(p.get("sku")):
        qs += [f'ANTA "{v}"', f'"{v}" ANTA shoe']
    if p.get("product_name"):
        qs += [f'ANTA "{p["product_name"]}" "{p["sku"]}"']
    seen=set(); candidates=[]
    d=DDGS()
    for q in dict.fromkeys(qs):
        try:
            for r in d.images(q,max_results=CFG["max_image_results"]):
                img=r.get("image") or r.get("thumbnail")
                src=r.get("url") or r.get("source") or ""
                title=r.get("title") or ""
                if img and img not in seen:
                    seen.add(img)
                    candidates.append((img,src,title,q))
        except Exception:
            pass
    good=[]
    for img,src,title,q in candidates:
        ok,w,h=image_ok(img)
        if not ok: continue
        sc=score(p,title,src)+(8 if min(w,h)>=900 else 4)
        good.append({"image":img,"source":src,"title":title,"query":q,"score":min(100,sc),"width":w,"height":h})
    good.sort(key=lambda x:x["score"],reverse=True)
    best=good[0] if good else None
    if best and best["score"]>=CFG["auto_publish_threshold"]:
        chosen=good[:CFG["max_images_per_product"]]
        for i in range(1,7):
            p[f"image_{i}_url"]=chosen[i-1]["image"] if i<=len(chosen) else ""
        p["image_source"]=best["source"]; p["image_confidence"]=str(best["score"]); p["image_status"]="AUTO_PUBLISHED"
        p["review_status"]="AUTO_APPROVED"; status="AUTO_PUBLISHED"
    elif best and best["score"]>=CFG["review_threshold"]:
        p["image_status"]="REVIEW_REQUIRED"; p["review_status"]="WEB_MATCH_REVIEW"; status="REVIEW_REQUIRED"
        new=not REVIEW.exists()
        with REVIEW.open("a",newline="",encoding="utf-8-sig") as f:
            cols=["sku","product_name","candidate_image","candidate_url","candidate_title","confidence","width","height","status"]
            w=csv.DictWriter(f,fieldnames=cols)
            if new: w.writeheader()
            w.writerow({"sku":p.get("sku"),"product_name":p.get("product_name"),"candidate_image":best["image"],"candidate_url":best["source"],
                        "candidate_title":best["title"],"confidence":best["score"],"width":best["width"],"height":best["height"],"status":"PENDING"})
    else:
        p["image_status"]="NOT_FOUND"; p["review_status"]="NO_IMAGE_MATCH"; status="NOT_FOUND"
    return p,{"sku":p.get("sku"),"status":status,"score":best["score"] if best else 0,
              "source":best["source"] if best else "","title":best["title"] if best else "",
              "image":best["image"] if best else "","candidates":len(candidates)}

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
        print(f"{n}/{len(idx)} {products[i].get('sku')}")
        products[i],diag=enrich(products[i]); out.append(diag)
        print(" ->",diag["status"],"score",diag["score"],diag["source"])
    PRODUCTS.write_text(json.dumps(products,ensure_ascii=False,indent=2))
    LOG.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print("SUMMARY")
    for x in out: print(x["sku"],x["status"],x["score"],x["title"])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit",type=int,default=10)
    ap.add_argument("--sku",action="append",default=[])
    a=ap.parse_args()
    main(a.limit,a.sku)
