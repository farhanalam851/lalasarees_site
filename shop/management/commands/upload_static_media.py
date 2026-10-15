"""Copy the photos in static/media/ into the configured bucket (same paths), so existing products keep their images."""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Upload static/media/** to the S3/Supabase bucket. Run once after adding the AWS_* variables."

    def handle(self, *args, **opts):
        if not settings.MEDIA_STORAGE_CONFIGURED:
            raise CommandError("Set AWS_STORAGE_BUCKET_NAME and the other AWS_* variables first.")
        root = Path(settings.BASE_DIR) / "static" / "media"
        done = skipped = 0
        for f in sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".gitkeep"):
            name = f.relative_to(root).as_posix()
            if default_storage.exists(name):
                skipped += 1
                continue
            with open(f, "rb") as fh:
                saved = default_storage.save(name, File(fh))
            done += 1
            self.stdout.write(f"uploaded {saved}")
        self.stdout.write(self.style.SUCCESS(f"Done. uploaded={done} already-there={skipped}"))
