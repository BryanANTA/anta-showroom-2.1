<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANTA Showroom Admin</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f5f5f5;color:#111}
header{background:#111;color:#fff;padding:25px 5%}
main{max-width:1400px;margin:auto;padding:28px 5%}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 10px #0001}
.num{font-size:32px;font-weight:bold}
.muted{color:#666}
.btn{background:#111;color:#fff;border:0;border-radius:7px;padding:10px 14px;cursor:pointer}
table{width:100%;border-collapse:collapse;background:#fff;margin-top:18px}
th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}
input{padding:10px;border:1px solid #ccc;border-radius:7px;width:300px;max-width:90%}
</style>
</head>
<body>
<header><h1>ANTA SHOWROOM — ADMIN</h1><div>Catalogue control centre</div>
<div style="margin-top:10px"><a href="retailers.html" style="color:white;margin-right:15px">Retailers</a><a href="analytics.html" style="color:white">Analytics</a></div></header>
<main>
<div class="grid">
  <div class="card"><div class="muted">Total Products</div><div class="num" id="total">—</div></div>
  <div class="card"><div class="muted">E-com Matches</div><div class="num" id="ecom">—</div></div>
  <div class="card"><div class="muted">Pending Review</div><div class="num" id="pending">—</div></div>
  <div class="card"><div class="muted">Web Enrichment Found</div><div class="num" id="web">—</div></div>
</div>

<div class="card" style="margin-top:20px">
<h2>Product Search</h2>
<input id="q" placeholder="SKU or product name">
<button class="btn" onclick="exportReview()">Export Review Queue</button>
<table>
<thead><tr><th>SKU</th><th>Product</th><th>Colour</th><th>Status</th><th>RRP</th></tr></thead>
<tbody id="rows"></tbody>
</table>
</div>
</main>
<script>
let P=[];
fetch('products.json').then(r=>r.json()).then(d=>{
  P=d;
  total.textContent=P.length.toLocaleString();
  ecom.textContent=P.filter(x=>x.description_match==='exact').length.toLocaleString();
  pending.textContent=P.filter(x=>x.review_status==='PENDING_REVIEW').length.toLocaleString();
  web.textContent=P.filter(x=>x.web_enrichment_status==='FOUND').length.toLocaleString();
  render();
});
function render(){
  let q=document.getElementById('q').value.toLowerCase();
  let a=P.filter(p=>!q||[p.sku,p.alternate_sku,p.product_name].join(' ').toLowerCase().includes(q)).slice(0,100);
  rows.innerHTML=a.map(p=>`<tr><td>${p.sku}</td><td>${p.product_name||''}</td><td>${p.colour||''}</td><td>${p.review_status||''}</td><td>${p.rrp||''}</td></tr>`).join('');
}
q.oninput=render;
function exportReview(){
  let a=P.filter(p=>p.review_status==='PENDING_REVIEW'||p.review_status==='WEB_MATCH_REVIEW');
  let csv='SKU,Alternate SKU,Product Name,Status,Web URL\n'+
    a.map(p=>[p.sku,p.alternate_sku,p.product_name,p.review_status,p.web_match_url]
      .map(v=>`"${String(v||'').replaceAll('"','""')}"`).join(',')).join('\n');
  let x=document.createElement('a');
  x.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  x.download='ANTA_Review_Queue.csv';
  x.click();
}
</script>
</body>
</html>