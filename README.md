# Lala Sarees: Django e-commerce (retail + wholesale)

Premium sarees for every occasion. P Road, Kanpur. 9211420021 / 9638527410.

## What's included
- **Storefront**: home, catalogue, collections, occasion filter, search, price filter, sort, product pages with gallery, ratings and reviews (with photos and "verified purchase").
- **Accounts**: register (individual or business with GSTIN), login, logout, password reset by email, profile, saved addresses.
- **B2B**: business accounts are approved by staff, then get wholesale prices automatically from the minimum quantity set on each product. Wholesale enquiry form.
- **Cart and checkout**: session cart, stock locking, live total update when the delivery state or payment method changes.
- **GST**: per-product GST % and HSN code, CGST+SGST for Uttar Pradesh deliveries and IGST for other states, printable GST invoice. Switch between GST-inclusive and GST-exclusive pricing with `PRICES_INCLUDE_GST` in settings.
- **Shipping**: UP rate, rest-of-India rate, free-shipping threshold, COD fee and COD limit. All editable in Admin > Store settings.
- **Payments**: Razorpay (cards, UPI, netbanking, with signature check and webhook), UPI QR (customer enters UTR, staff verifies), bank transfer, cash on delivery.
- **Staff dashboard** at `/dashboard/`: sales overview, orders (status, courier, tracking, payment verification), products (add/edit/hide), customers (wholesale approval), enquiries, review moderation. Full Django admin at `/admin/`.
- **Responsive** for phones, tablets and desktop, with a saree-inspired look (pallu border bands, mehrab arches, zari gold).

## Run it locally
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser                      # email, first name, password
python manage.py seed_demo                            # loads the 8 sample sarees from seed_images/
python manage.py runserver
```
Open http://127.0.0.1:8000/ and http://127.0.0.1:8000/dashboard/ (log in with the superuser).
Optional: `python manage.py seed_demo --with-demo-users` adds demo buyers and reviews (delete them before going live).

## Before going live (important)
1. **Store settings**: Admin > Store settings. Enter your GSTIN, UPI ID, bank details, shipping rates, COD rules.
2. **Razorpay**: create an account, then set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` as environment variables. In the Razorpay dashboard add the webhook `https://YOURDOMAIN/pay/razorpay/webhook/` with events `payment.captured` and `order.paid`. Test in Razorpay test mode first.
3. **UPI QR**: set the UPI ID in Store settings. Orders stay "Verifying" until staff confirms the UTR in Dashboard > Verify payments. (Fully automatic UPI confirmation needs a payment gateway, which Razorpay already provides.)
4. **GST**: the seed data uses 5% GST and HSN 5407. Ask your CA to confirm the rate and HSN for each product (rates depend on the price slab and fabric), and whether shipping charges need GST on invoices. Edit per product in the dashboard.
5. **Photos**: the supplied sample images are stock photos (some carry Pngtree watermarks). Replace them with your own product photography in Dashboard > Products.
6. **Policies**: pages under `templates/pages/` are templates. Have a legal adviser review them.
7. **Deploy on Vercel**: follow `DEPLOY_VERCEL.md` (Postgres + bucket for photos, no SQLite).
8. **Deploy on your own server instead**: set the variables in `.env.example`, `DJANGO_DEBUG=0`, run `python manage.py collectstatic`, serve with gunicorn behind nginx, and let nginx serve `/media/`. Use PostgreSQL by setting `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`. Configure SMTP (`EMAIL_HOST`...) so order and password-reset emails send.

## Layout
```
lalasarees/   settings, urls
accounts/     custom user (email login), addresses, GST state codes
shop/         catalogue, reviews, enquiries, store settings, seed_demo command
orders/       cart, tax.py (GST maths), orders, payments, invoice
dashboard/    staff dashboard
templates/    all HTML      static/  css + js      seed_images/  your supplied photos
```

## SEO and launch checklist (what is built in, and what only you can do)
**Built in**
- Server-side rendered HTML (Django), so Google sees full content without running JavaScript.
- Unique `<title>` and meta description on every public page, `<h1>` on every page, canonical tags, Open Graph + Twitter card, `og-image.jpg` (1200x630).
- `noindex` on cart, checkout, account, orders, thank-you, search and filtered catalogue pages; public pages are indexable.
- `/robots.txt` (blocks only private areas, points to the sitemap) and `/sitemap.xml` (pages, collections, every live product).
- Structured data: LocalBusiness on home, Product + AggregateRating + BreadcrumbList on products, BreadcrumbList on catalogue, FAQPage on Shipping and returns. (Google now shows FAQ rich results only for a few site types, so expect no FAQ snippet. It is harmless.)
- One-hop redirect to your canonical host (set `DJANGO_CANONICAL_HOST=www.yourdomain.in`), so http, https, www never chain.
- Images: alt text everywhere, width/height set (no layout shift), lazy loading, hero preloaded, every upload auto-converted to WebP and capped at 1400px. Gzip and 1-year static caching are on.
- Favicon set, web manifest, custom 404, thank-you pages (order and enquiry), cookie banner, GA4 (loads only after consent; set `GA_MEASUREMENT_ID`), form error and loading states, sticky mobile CTA on home and product pages, privacy and terms pages.

**Only you can do (needs your accounts / the live domain)**
1. Deploy to a public domain over HTTPS. A site that is only on a laptop or localhost cannot appear in Google.
2. Search Console: add the domain property, verify it (DNS record), then Sitemaps > submit `https://yourdomain.in/sitemap.xml`. Use URL Inspection > Request indexing for the home page and top collections.
3. Create a free **Google Business Profile** for the P Road shop (the strongest local ranking signal for "saree shop Kanpur"), and list on IndiaMART / JustDial for wholesale.
4. Replace the sample product copy and photos with real ones, and write an owner/shop story for the About page (Google rewards first-hand, specific content).
5. Run PageSpeed Insights on the live URL to confirm load speed. It depends on your server, so I cannot promise a number from here.
