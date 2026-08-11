# Deploying the showroom

1. Put this folder in a GitHub repository.
2. Enable GitHub Pages from Settings -> Pages.
3. Select the `main` branch and `/root` (or repository root).
4. The `index.html` showroom is then publicly accessible.
5. GitHub Actions runs the enrichment worker on its schedule.

Important: automated web access must comply with each site's robots.txt and terms.
Do not add API keys to the repository. If a search provider requires a key,
store it as a GitHub Actions secret and adapt `SEARCH_URL_TEMPLATE`/the search
function to that provider's documented API.
