"""Convert uploaded images to WebP and cap their size, so every upload is web-fast."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimise(field_file, max_side=1400, quality=82):
    """Call before save() on a model with an ImageField. Only touches fresh uploads."""
    if not field_file or getattr(field_file, "_committed", True):
        return
    try:
        field_file.file.seek(0)
        im = ImageOps.exif_transpose(Image.open(field_file.file))
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        im.thumbnail((max_side, max_side))
        buf = BytesIO()
        im.save(buf, "WEBP", quality=quality, method=6)
        name = Path(field_file.name).stem + ".webp"
        field_file.save(name, ContentFile(buf.getvalue()), save=False)
    except Exception:
        # leave the original upload untouched if it cannot be processed
        field_file.file.seek(0)
