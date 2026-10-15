"""Run on your computer BEFORE/AFTER deploying: python manage.py check_deploy"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Checks the settings Vercel needs and tests the database connection."

    def handle(self, *args, **opts):
        ok = True

        def line(good, text):
            nonlocal ok
            ok = ok and good
            self.stdout.write((self.style.SUCCESS("  OK    ") if good else self.style.ERROR("  FIX   ")) + text)

        key_ok = settings.SECRET_KEY != settings.INSECURE_DEFAULT_KEY
        line(key_ok, "DJANGO_SECRET_KEY is set" if key_ok else "DJANGO_SECRET_KEY is not set (needed on Vercel)")
        db_set = bool(settings.DATABASE_URL)
        line(db_set, "DATABASE_URL is set" if db_set else "DATABASE_URL is not set (using local SQLite; fine on your PC, NOT on Vercel)")
        if db_set:
            d = settings.DATABASES["default"]
            self.stdout.write(f"        host={d['HOST']} port={d['PORT']} user={d['USER']} db={d['NAME']}")
            if "pooler.supabase.com" in d["HOST"] and not d["USER"].startswith("postgres."):
                line(False, "Supabase pooler user must look like postgres.PROJECTREF (copy the string from Connect)")
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            line(True, f"database connection works ({connection.vendor})")
            tables = connection.introspection.table_names()
            line("shop_product" in tables, "tables exist" if "shop_product" in tables else "tables missing: run python manage.py migrate")
            if "shop_product" in tables:
                from shop.models import Product
                n = Product.objects.count()
                self.stdout.write(f"        products in database: {n}" + ("  (run: python manage.py seed_demo)" if n == 0 else ""))
        except Exception as exc:  # noqa: BLE001
            line(False, f"cannot connect to the database: {exc.__class__.__name__}: {str(exc).strip()[:300]}")
        self.stdout.write("  INFO  photos: " + ("bucket (S3-compatible)" if settings.MEDIA_STORAGE_CONFIGURED
                                                 else "demo photos from static/media (no bucket; dashboard uploads will not persist on Vercel)"))
        self.stdout.write(self.style.SUCCESS("\nAll good." ) if ok else self.style.ERROR("\nFix the items marked FIX, then run this again."))
