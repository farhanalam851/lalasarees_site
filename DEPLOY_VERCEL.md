# Deploying Lala Sarees on Vercel with Supabase

Vercel's disk is read-only, so SQLite cannot be used. The database is **Supabase Postgres**.
The 8 demo sarees and 5 categories ship their photos inside the site (`static/media/`), so they show without any file storage.
Photos you upload later through the dashboard need Supabase Storage (last section) to last.

## 0. Make sure Vercel gets the NEW files
Your repo must contain this version. Check: `lalasarees/wsgi.py` has `def missing_settings()` and the folder `static/media/products/` has 8 photos.
(An older version crashed with "AWS_STORAGE_BUCKET_NAME is not set". That means old files are still deployed.)

## 1. Supabase
1. supabase.com > New project. Region: **Mumbai (ap-south-1)**. Save the database password (use letters and numbers only, it avoids URL problems).
2. Click **Connect** (top bar) > tab **Connection string**. You need two strings. Replace `[YOUR-PASSWORD]` in each with your password.
   - **Transaction pooler** (port **6543**): for Vercel.
     `postgresql://postgres.PROJECTREF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`
   - **Session pooler** (port **5432**): for running migrations from your computer.
     `postgresql://postgres.PROJECTREF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
   The username is `postgres.PROJECTREF`, not just `postgres`. Copy the strings from the dashboard, do not type them.
   Use the pooler strings, not "Direct connection": direct is IPv6-only and fails on Vercel and many home networks.
   If your password contains `@ # / :` replace them with `%40 %23 %2F %3A`.

## 2. GitHub
Push this folder to a private repo (`manage.py` at the repo root).

## 3. Vercel
Import the repo. Add these Environment Variables (Production and Preview), then deploy:

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | run `python -c "import secrets;print(secrets.token_urlsafe(60))"` |
| `DATABASE_URL` | the **Transaction pooler** string (port 6543) |

Variables added after a deploy only apply after **Redeploy**.

## 4. Create tables and demo products (once, from your computer)
```bash
pip install -r requirements.txt
```
Set `DATABASE_URL` in your terminal to the **Session pooler** string (port 5432). Do not set `VERCEL`.
- Windows PowerShell: `$env:DATABASE_URL="postgresql://..."`
- Command Prompt: `set DATABASE_URL=postgresql://...`
- macOS/Linux: `export DATABASE_URL="postgresql://..."`

```bash
python manage.py check_deploy        # shows what is missing, tests the connection
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo           # the 8 demo sarees
python manage.py check_deploy        # should end with "All good."
```
Optional: `seed_demo --with-demo-users` adds sample customers and reviews. Never on the live site.

## 5. Lock the tables (important, once)
Supabase exposes tables through a public API. Django does not use it, so switch it off for your tables.
Supabase > **SQL Editor** > New query > paste > Run:
```sql
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $$;
```
The site keeps working (it connects as the `postgres` role, which is not affected). Run it again after future migrations that add tables.

## 6. Check
Open `https://YOUR-PROJECT.vercel.app/healthz/`. Expect `"ok": true, "database": "postgresql"`. Then the home page shows the sarees with photos. Admin: `/admin/`. Staff dashboard: `/dashboard/`. Errors: Vercel > Logs.

## 7. Custom domain
Add the domain in Vercel, then set `DJANGO_CANONICAL_HOST=www.yourdomain.in` and redeploy.

## Real photo uploads (Supabase Storage)
1. Supabase > Storage > New bucket `media`, tick **Public bucket**.
2. Storage > Settings > **S3 Connection**: copy the endpoint and create an access key (ID and secret).
3. Add these Vercel variables and redeploy (`PROJECTREF` = the part before `.supabase.co` in your project URL):

| Name | Value |
|---|---|
| `AWS_STORAGE_BUCKET_NAME` | `media` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | from step 2 |
| `AWS_S3_ENDPOINT_URL` | `https://PROJECTREF.storage.supabase.co/storage/v1/s3` |
| `AWS_S3_REGION_NAME` | `ap-south-1` |
| `AWS_S3_CUSTOM_DOMAIN` | `PROJECTREF.supabase.co/storage/v1/object/public/media` |

The site then stores new uploads in the bucket. The 13 demo photos already in the database point at `products/...` and `categories/...`,
so upload the files from `static/media/products` and `static/media/categories` into those folders of the bucket (Storage > media > upload), or just re-add products with your own photos.

## Limits
- Uploads over about 4.5 MB fail on Vercel. Resize photos first.
- Vercel's free Hobby plan is for non-commercial use; a live shop should use Pro.
- Supabase free projects pause after a week without activity (restore with one click). Pro avoids it.
- Order and password-reset emails need the `EMAIL_*` variables (see `.env.example`).
