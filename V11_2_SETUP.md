# ANTA V11.2

V11.2 changes the matching flow:

1. Search for confirmed product pages first.
2. Reject collection/category/search pages.
3. Score exact SKU, regional 1/8 SKU, SKU stems and product-name tokens.
4. Only after a strong product-page match, extract images from that page.
5. Validate image dimensions.
6. Auto-publish only at 90+ confidence.
7. Send 70-89 matches to review.

FIRST TEST

Run:
ANTA V11.2 Confirmed Product Page Updater

limit:
5

skus:
312039901-1,312039902-1,312039902-2,312121102-4,312121110-1

The log now prints confirmed page URL, score and number of valid images.
