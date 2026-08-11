# V11.1 FIRST TEST

Upload V11.1 into the same GitHub repo.

New files:
- v11_1_image_updater.py
- v11_1_config.json
- .github/workflows/v11-1-better-images.yml

Replace requirements.txt.

Then run:
Actions -> ANTA V11.1 Better Image Updater

limit:
5

skus:
312039901-1,312039902-1,312039902-2,312121102-4,312121110-1

The workflow log now prints:
AUTO_PUBLISHED / REVIEW_REQUIRED / NOT_FOUND
plus score and source.
