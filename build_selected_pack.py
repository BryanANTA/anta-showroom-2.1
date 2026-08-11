#!/usr/bin/env python3
"""
Build selected ANTA product packs.

Input:
  products.json from the showroom
  selected_skus.txt OR --sku arguments

Output:
  ANTA_SELECTED_PRODUCTS.zip

Only downloads image URLs that are present in the catalogue and publicly
accessible. It does not bypass authentication, CAPTCHAs, robots controls,
or hotlink protections. If an image cannot be fetched, its URL is recorded
in IMAGE_SOURCES.txt instead.
"""
import argparse, json, os, re, zipfile
from pathlib import Path
from io import BytesIO
import requests

ROOT=Path(__file__).resolve().parent
UA="ANTA-Showroom-Packager/1.0"
HEAD={"User-Agent":UA}

def safe(s):
    s=re.sub(r'[\\/:*?"<>|]+','_',str(s or ''))
    return re.sub(r'\s+',' ',s).strip()[:100] or "ANTA_PRODUCT"

def get_image(url, timeout=20):
    try:
        r=requests.get(url,headers=HEAD,timeout=timeout,stream=True)
        r.raise_for_status()
        ctype=r.headers.get("content-type","").lower()
        if not ctype.startswith("image/"):
            return None
        return r.content
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sku",action="append",default=[])
    ap.add_argument("--selected-file",default="")
    ap.add_argument("--output",default="ANTA_SELECTED_PRODUCTS.zip")
    args=ap.parse_args()

    products=json.loads((ROOT/"products.json").read_text(encoding="utf-8"))
    wanted=set(x.strip().upper() for x in args.sku if x.strip())
    if args.selected_file:
        wanted.update(x.strip().upper() for x in Path(args.selected_file).read_text().splitlines() if x.strip())

    if not wanted:
        raise SystemExit("No SKUs supplied.")

    selected=[]
    for p in products:
        if str(p.get("sku","")).upper() in wanted or str(p.get("alternate_sku","")).upper() in wanted:
            selected.append(p)

    if not selected:
        raise SystemExit("No matching SKUs found.")

    temp=ROOT/"_selected_pack"
    if temp.exists():
        import shutil; shutil.rmtree(temp)
    temp.mkdir()

    for p in selected:
        folder=temp/(safe(f'{p.get("sku","")}_{p.get("product_name","")}'))
        folder.mkdir()
        info={
            "SKU":p.get("sku",""),
            "Alternate SKU":p.get("alternate_sku",""),
            "Product Name":p.get("product_name",""),
            "Colour":p.get("colour",""),
            "Category":p.get("category",""),
            "Product Type":p.get("product_type",""),
            "Product Sub-Type":p.get("product_sub_type",""),
            "Material":p.get("material",""),
            "Outsole":p.get("outsole",""),
            "Closure":p.get("closure",""),
            "RRP":p.get("rrp",""),
            "Description":p.get("ecom_description") or p.get("short_description") or p.get("long_description",""),
            "Features":p.get("features") or p.get("ecom_features",""),
            "Web Source":p.get("web_match_url",""),
            "Match Confidence":p.get("web_match_confidence","")
        }
        (folder/"Product_Info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf-8")
        (folder/"Product_Description.txt").write_text(info["Description"],encoding="utf-8")
        urls=[p.get(f"image_{i}_url","") for i in range(1,7)]
        sources=[]
        for n,u in enumerate(urls,1):
            if not u: continue
            data=get_image(u)
            if data:
                ext=".jpg"
                c=u.lower()
                if ".png" in c: ext=".png"
                elif ".webp" in c: ext=".webp"
                (folder/f"Image_{n:02d}{ext}").write_bytes(data)
            sources.append(f"Image_{n:02d}: {u}")
        (folder/"IMAGE_SOURCES.txt").write_text("\n".join(sources),encoding="utf-8")

    out=ROOT/args.output
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for root,dirs,files in os.walk(temp):
            for f in files:
                path=Path(root)/f
                z.write(path,path.relative_to(temp))
    print(out)

if __name__=="__main__":
    main()
