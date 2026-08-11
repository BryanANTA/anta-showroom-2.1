# Optional: Simple User Access with Cloudflare

Use this only if you want to restrict the showroom to approved people.

Recommended experience:

Retailer opens showroom URL
-> Cloudflare asks for email
-> retailer receives a one-time code
-> showroom opens

No retailer passwords to manage.

You remain in control of which emails/domains are allowed.

This access layer sits in front of the V10 website, so the showroom files do not
need Supabase or a retailer database.

Typical setup:
1. Add your domain to Cloudflare.
2. Open Cloudflare Zero Trust.
3. Create an Access Application for the showroom hostname.
4. Add an Allow policy.
5. Allow specific retailer email addresses or approved company domains.
6. Use One-Time PIN as the login method.

If you keep only the default github.io address, using a custom domain is the cleaner
way to place Cloudflare Access in front of the showroom.
