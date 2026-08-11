# ANTA Showroom V10 — Deploy Ready

## FASTEST GITHUB SETUP

### 1. Create repository
Create a GitHub repository called:

`anta-showroom`

### 2. Upload this package
Unzip this file.

Upload the CONTENTS of the folder to the root of your GitHub repository.

Important:
`index.html` must be visible in the root of the repository.

### 3. Commit
Click:

`Commit changes`

### 4. Enable GitHub Pages
Open:

Settings -> Pages

Under Build and deployment choose:

`GitHub Actions`

The included workflow:

`.github/workflows/deploy-pages.yml`

will publish the showroom automatically.

### 5. Your showroom address
It should become:

`https://YOUR-GITHUB-USERNAME.github.io/anta-showroom/`

### 6. Main pages

Retailer entry:
`/login.html`

Catalogue:
`/index.html`

Admin dashboard:
`/admin.html`

### 7. Simple protection
GitHub Pages itself is public.

For approved-user access, put Cloudflare Access in front of the site or use another
hosting provider with access control.

The catalogue code does not need to change.

## IMPORTANT
Do not upload private passwords or API secrets into GitHub.

This version does not require Supabase.
