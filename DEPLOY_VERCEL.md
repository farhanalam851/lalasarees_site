# Deploying Lala Sarees on Vercel (Neon database, demo photos, no bucket yet)

Vercel's disk is read-only, so SQLite cannot be used. The database is **Neon**. The 8 demo sarees and 5 categories ship
their photos inside the site (`static/media/`), so they show up without any file storage.

**Limit of this setup:** photos you upload later through the dashboard will NOT last on Vercel. Add a bucket
(Cloudflare R2, see the end of this file) before you start adding real products.

## 1. Neon
1. neon.tech > create a project. Region: Singapore.
2. Connect > tick **Connection pooling** > copy the string (host has `-pooler`). This is `DATABASE_URL` on Vercel.
3. Connect > untick pooling > copy the string. This **direct** one is only for step 4.

## 2. GitHub
Upload this folder to a private repo (`manage.py` at the repo root).

## 3. Vercel
Import the repo, add two environment variables, deploy:

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | run `python -c "import secrets;print(secrets.token_urlsafe(60))"` |
| `DATABASE_URL` | Neon **pooled** string |

## 4. Create tables and load demo products (once, from your computer)
```bash
pip install -r requirements.txt
```
Set `DATABASE_URL` to the Neon **direct** string (macOS/Linux `export DATABASE_URL="..."`, PowerShell `$env:DATABASE_URL="..."`). Do not set `VERCEL`. Then:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
```
Optional: add `--with-demo-users` for sample customers and reviews (delete them before going live).

## 5. Check
Open `https://YOUR-PROJECT.vercel.app/healthz/` (expect `"ok": true`, `"database": "postgresql"`), then the home page: the 8 sarees should show with photos. Admin is at `/admin/`, staff dashboard at `/dashboard/`. Errors appear in Vercel > Logs.

## 6. Custom domain
Add the domain in Vercel, then set `DJANGO_CANONICAL_HOST=www.yourdomain.in` and redeploy.

## Later: real photo uploads (Cloudflare R2)
Create an R2 bucket with a public `r2.dev` URL and an Object Read & Write token, then add these Vercel variables:
`AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_S3_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com`, `AWS_S3_REGION_NAME=auto`, `AWS_S3_CUSTOM_DOMAIN=pub-xxxx.r2.dev`.
The site switches to the bucket automatically. Demo photos already in the database keep working only if you also upload
`static/media/products` and `static/media/categories` into the bucket under `products/` and `categories/`.

## Other limits
- Uploads over about 4.5 MB fail on Vercel. Resize photos first.
- Vercel's free Hobby plan is for non-commercial use; a live shop should use Pro.
- Order and password-reset emails need the `EMAIL_*` variables (see `.env.example`).
