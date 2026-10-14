# Deploying Lala Sarees on Vercel

Vercel runs Django as a serverless function. Two things from a normal server do not exist there:
the disk is read-only (so **no SQLite**) and uploaded files are not kept (so **photos need a bucket**).
This project is already set up for that. You only need a free Postgres database and a free storage bucket.
Supabase gives you both in one account, so the steps below use it. Neon + Cloudflare R2 also work.

Pick the **Mumbai (ap-south-1)** region in Supabase. `vercel.json` already runs the site in Mumbai (`bom1`).

## 1. Supabase (database + photos)
1. Create a project (Mumbai). Save the database password.
2. **Database URL**: Project > Connect > *Transaction pooler* string, port **6543**. It looks like
   `postgresql://postgres.xxxx:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`.
   If your password has symbols like `@ # /`, replace them with `%40 %23 %2F`.
   This is your `DATABASE_URL`.
3. **Storage** > New bucket named `media`, tick **Public bucket**.
4. Storage > Settings > **S3 connection** > New access key. Copy the Access key ID and Secret.
   `PROJECT_REF` below is the part before `.supabase.co` in your project URL.

## 2. Put the code on GitHub
Upload this folder to a **private** repo (`manage.py` must be at the repo root). `.gitignore` already keeps secrets and the local database out.

## 3. Vercel
1. vercel.com > Add New > Project > import the repo. Framework is detected as Django. Leave build settings alone.
2. Before the first deploy, add these Environment Variables (Production + Preview). Full list with examples in `.env.example`.

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | run `python -c "import secrets;print(secrets.token_urlsafe(60))"` |
| `DATABASE_URL` | Supabase pooler URL from step 1 |
| `AWS_STORAGE_BUCKET_NAME` | `media` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | from step 1.4 |
| `AWS_S3_ENDPOINT_URL` | `https://PROJECT_REF.storage.supabase.co/storage/v1/s3` |
| `AWS_S3_REGION_NAME` | `ap-south-1` |
| `AWS_S3_CUSTOM_DOMAIN` | `PROJECT_REF.supabase.co/storage/v1/object/public/media` |

3. Deploy.

## 4. Create the tables (once, from your computer)
Vercel does not run migrations for you. Run them once against the same database:

```bash
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Set the same variables in your terminal (macOS/Linux `export NAME="value"`, Windows PowerShell `$env:NAME="value"`):
`DATABASE_URL`, `DJANGO_SECRET_KEY`, and the `AWS_*` ones. Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo        # optional: loads the 8 sample sarees (uploads their photos to the bucket)
```
After any future model change: run `makemigrations`, commit the new migration files, push, then run `migrate` again.

## 5. Check it
Open `https://YOUR-PROJECT.vercel.app/healthz/`. You want:
`{"ok": true, "database": "postgresql", "media_storage": true, "debug": false}`.
Then log in at `/admin/` and `/dashboard/`, add a product with a photo, and open it.

If something is wrong, Vercel > your project > **Logs** shows the exact error. A missing setting is reported by name
("Deployment settings missing: DATABASE_URL is not set ...").

## 6. Custom domain
Vercel > Settings > Domains > add `www.yourdomain.in` (and the bare domain, redirecting to www). Then add the env var
`DJANGO_CANONICAL_HOST=www.yourdomain.in` and redeploy. Do this **after** the domain works, because it redirects every
other host (including `*.vercel.app`) to the canonical one.
Then: Razorpay webhook `https://www.yourdomain.in/pay/razorpay/webhook/` (events `payment.captured`, `order.paid`),
Search Console sitemap `https://www.yourdomain.in/sitemap.xml`.

## Limits to know about
- **Uploads over about 4.5 MB fail** on Vercel (platform limit on request size). Resize phone photos before uploading.
  Every upload is converted to WebP and capped at 1400px after it arrives.
- Vercel's free Hobby plan is for non-commercial use. A live shop that takes orders should be on Pro.
- Supabase free projects pause after a week of no activity. A shop with traffic will not hit this, but a demo might.
- Emails (order mail, password reset) need the `EMAIL_*` variables. Without them Django only prints emails to the log.
- Never run `seed_demo --with-demo-users` against the live database.
