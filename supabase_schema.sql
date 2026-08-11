name: ANTA showroom enrichment

on:
  workflow_dispatch:
  schedule:
    - cron: '17 2 * * 1,3,5'

permissions:
  contents: write

jobs:
  enrich:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python scraper.py --limit 100
      - name: Commit enrichment
        run: |
          git config user.name "anta-showroom-bot"
          git config user.email "actions@users.noreply.github.com"
          git add products.json
          git commit -m "Update ANTA showroom enrichment" || exit 0
          git push
