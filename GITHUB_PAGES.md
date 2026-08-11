#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--skus",required=True,help="Comma-separated SKUs")
    ap.add_argument("--output",default="selected_manifest.json")
    args=ap.parse_args()
    products=json.loads(Path("products.json").read_text(encoding="utf-8"))
    wanted={x.strip().upper() for x in args.skus.split(",") if x.strip()}
    rows=[]
    for p in products:
        if p.get("sku","").upper() in wanted or p.get("alternate_sku","").upper() in wanted:
            rows.append(p)
    manifest={"count":len(rows),"skus":[p["sku"] for p in rows],"products":rows}
    Path(args.output).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(args.output)
if __name__=="__main__": main()
