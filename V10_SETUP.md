# ANTA Showroom V10 — Simplified Setup

This version keeps the V9 catalogue, SKU matching, selection and download features,
but removes the requirement for Supabase.

## Recommended simple setup

### 1. GitHub
Upload all files to a GitHub repository.

### 2. GitHub Pages
Enable Pages:
Settings -> Pages -> Deploy from branch -> main -> /root

### 3. Protect access
Use a hosting/access layer such as Cloudflare Access if you want approved users only.

Retailer flow:
Showroom URL -> hosting access check -> showroom

Admin flow:
Private admin URL -> hosting access check -> admin.html

## Main pages
- login.html
- index.html
- admin.html
- retailers.html
- analytics.html

## What remains from V9
- 3,859-product catalogue
- 1/8 regional SKU matching
- e-commerce descriptions
- search and filters
- product selection
- selected downloads
- CSV export
- complete-product-pack workflow
- background enrichment structure

## What has been removed from the required setup
- Supabase login
- retailer database
- database policies
- passwordless auth configuration

The optional Supabase files are retained under `optional_supabase_backend/` if you want
to restore detailed retailer tracking later.
