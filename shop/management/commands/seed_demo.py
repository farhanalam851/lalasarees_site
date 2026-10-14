from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import User
from shop.models import Category, Product, Review, SiteConfig

IMG = Path(settings.BASE_DIR) / "seed_images"

CATEGORIES = [
    ("Ready-to-Wear Sarees", "Pre-draped and stitched. Wear in under a minute.", "black-predrape.webp", "50% 25%"),
    ("Designer & Party", "Sequins, tissue and embroidered blouses for the evening.", "green-tissue.webp", "50% 25%"),
    ("Wedding & Zari", "Georgette and silk with heavy zari borders.", "teal-embroidered.webp", "58% 45%"),
    ("Silk Sarees", "Kanjivaram-style silk with woven gold motifs.", "silk-zari.webp", "50% 50%"),
    ("Everyday Elegance", "Light drapes with contrast borders for daily and office wear.", "sage-peach.webp", "57% 45%"),
]

# name, category, occasion, fabric, color, image, focus, price, mrp, wholesale, gst, featured, description
PRODUCTS = [
    ("Blush Pink Ruffle-Border Ready-to-Wear Saree", 0, "party", "Lycra blend", "Blush pink", "pink-ruffle.webp", "50% 20%", 3499, 4999, 2650, 5, True,
     "A pre-draped saree with a ruffled pallu edge and a hand-embellished blouse. Pleats are stitched in place, so it drapes the same way every time."),
    ("Midnight Black Pre-Draped Saree with Sequin Blouse", 0, "party", "Satin lycra", "Black", "black-predrape.webp", "50% 25%", 4299, 5999, 3300, 5, True,
     "Sleek black pre-draped saree with a sequin-and-bead blouse and an embellished belt. Slip in, pin the pallu and go."),
    ("Navy Blue Sequin Blouse Pre-Draped Saree", 0, "party", "Satin lycra", "Navy blue", "navy-predrape.webp", "50% 25%", 4499, 6299, 3450, 5, False,
     "Deep navy ready-to-wear drape with a fully sequinned sweetheart-neck blouse. Made for cocktail evenings and receptions."),
    ("Pista Green Tissue Zari Saree with Embroidered Blouse", 1, "wedding", "Tissue organza", "Pista green", "green-tissue.webp", "50% 40%", 5999, 8499, 4700, 5, True,
     "Shimmering tissue saree with gold zari running through the weave, paired with a pearl-and-mirror embroidered blouse with tassel hem."),
    ("Ivory Cocktail Drape Saree with Gold Sequin Blouse", 1, "party", "Georgette lycra", "Ivory", "ivory-drape.webp", "50% 30%", 5499, 7499, 4200, 5, False,
     "Soft ivory drape with a gold-sequin halter blouse. Quietly dramatic for engagement parties and receptions."),
    ("Teal Georgette Saree with Rose Zari Embroidery", 2, "wedding", "Georgette", "Teal and magenta", "teal-embroidered.webp", "58% 45%", 7999, 10999, 6200, 5, True,
     "Sheer teal georgette with hand-embroidered magenta roses, a wide zari border and a rich gold-pink pallu. A wedding-season favourite."),
    ("Magenta & Plum Zari Silk Saree with Paisley Butta", 3, "festive", "Pure-feel silk", "Magenta and plum", "silk-zari.webp", "50% 50%", 6499, 8999, 5100, 5, True,
     "Woven silk with paisley buttas and a contrast zari border. Pairs well with temple jewellery."),
    ("Sage Green Saree with Peach Zari Border", 4, "office", "Cotton silk", "Sage and peach", "sage-peach.webp", "57% 45%", 2499, 3499, 1850, 5, False,
     "A calm sage body with a peach zari border and a gradient pallu. Light enough for the whole day."),
]


class Command(BaseCommand):
    help = "Load Lala Sarees demo catalogue using the supplied product photos."

    def add_arguments(self, parser):
        parser.add_argument("--with-demo-users", action="store_true", help="Also create demo customers and reviews (do NOT use in production).")

    def handle(self, *args, **opts):
        if not settings.MEDIA_STORAGE_CONFIGURED:
            self.stdout.write("No photo bucket set: demo photos will be served from static/media/ (they ship with the site).")
        cfg = SiteConfig.get()
        self.stdout.write("Store settings ready (edit in /admin/shop/siteconfig/).")

        cats = []
        for i, (name, desc, img, pos) in enumerate(CATEGORIES):
            c, created = Category.objects.get_or_create(name=name, defaults={"description": desc, "sort_order": i, "image_position": pos})
            if created and (IMG / img).exists():
                if settings.MEDIA_STORAGE_CONFIGURED:
                    with open(IMG / img, "rb") as f:
                        c.image.save(img, File(f), save=True)
                else:  # no bucket: images ship with the site as static files (static/media/...)
                    c.image.name = f"categories/{img}"
                    c.save()
            cats.append(c)

        for n, (name, ci, occ, fabric, color, img, pos, price, mrp, wh, gst, feat, desc) in enumerate(PRODUCTS, start=1):
            if Product.objects.filter(name=name).exists():
                continue
            p = Product(name=name, sku=f"LS-{n:03d}", category=cats[ci], occasion=occ, fabric=fabric, color=color,
                        description=desc, price=Decimal(price), mrp=Decimal(mrp), wholesale_price=Decimal(wh),
                        wholesale_min_qty=6, gst_rate=Decimal(gst), stock=25, is_featured=feat, image_position=pos)
            if settings.MEDIA_STORAGE_CONFIGURED:
                with open(IMG / img, "rb") as f:
                    p.image.save(img, File(f), save=False)
            else:
                p.image.name = f"products/{img}"
            p.save()

        if opts["with_demo_users"]:
            buyer, _ = User.objects.get_or_create(email="demo.buyer@example.com", defaults={"first_name": "Anjali", "phone": "9876543210"})
            buyer.set_password("DemoPass#123"); buyer.save()
            biz, _ = User.objects.get_or_create(email="demo.boutique@example.com", defaults={
                "first_name": "Ritu", "phone": "9876500000", "account_type": "business",
                "business_name": "Ritu Boutique", "gstin": "09ABCDE1234F1Z5", "wholesale_approved": True})
            biz.set_password("DemoPass#123"); biz.save()
            samples = [(buyer, 5, "Looks stunning", "The drape sits perfectly and the blouse work is lovely. Got many compliments."),
                       (biz, 4, "Good for resale", "Finish is neat and customers like the colours. Fast dispatch.")]
            for p in Product.objects.all()[:5]:
                for u, r, t, c in samples:
                    Review.objects.get_or_create(product=p, user=u, defaults={"rating": r, "title": t, "comment": c, "verified_purchase": True})
            self.stdout.write(self.style.WARNING("Demo users created: demo.buyer@example.com / demo.boutique@example.com, password DemoPass#123. Delete them before going live."))
        self.stdout.write(self.style.SUCCESS("Demo catalogue loaded."))
