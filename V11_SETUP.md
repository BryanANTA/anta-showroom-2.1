# ANTA Showroom V11

Built on V10.

Adds:
- exact SKU image search
- 1/8 regional SKU search
- product-name-assisted matching
- confidence scoring
- automatic publish for high-confidence matches
- review queue for uncertain matches
- scheduled GitHub Action

FIRST TEST:
GitHub -> Actions -> ANTA V11 Auto Image Updater -> Run workflow
Set limit to 10.

Upload V11 into the SAME repo:
bryananta/anta-showroom-2.1

Replace existing files when prompted.

Important new files:
- v11_image_updater.py
- v11_config.json
- .github/workflows/v11-auto-images.yml
- requirements.txt

Also replace products.json and index.html from this package.
