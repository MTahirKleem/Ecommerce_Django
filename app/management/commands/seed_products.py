import mimetypes
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from app.models import (
    Additional_Information,
    Category,
    Product,
    Product_Image,
    banner_area,
    slider,
)

# Curated catalog: meaningful names + stable public product images
SEED_CATALOG = [
    {
        "category": "Electronics",
        "products": [
            {
                "name": "Sony WH-1000XM5 Wireless Headphones",
                "brand": "Sony",
                "price": 34999,
                "discount": 12,
                "shipping_fee": 199,
                "qty": 80,
                "available": 65,
                "description": (
                    "<p>Industry-leading noise cancellation, 30-hour battery life, "
                    "and crystal-clear hands-free calling for travel and work.</p>"
                ),
                "specs": [("Driver", "30 mm"), ("Connectivity", "Bluetooth 5.2"), ("Weight", "250 g")],
                "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Apple AirPods Pro (2nd Gen)",
                "brand": "Apple",
                "price": 59999,
                "discount": 8,
                "shipping_fee": 0,
                "qty": 120,
                "available": 90,
                "description": (
                    "<p>Active Noise Cancellation, Adaptive Audio, and MagSafe charging "
                    "case with precise Find My support.</p>"
                ),
                "specs": [("Chip", "H2"), ("Water resistance", "IPX4"), ("Battery", "Up to 30 hrs")],
                "image": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1588423771073-b8903fbb85b5?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Samsung 55-Inch 4K Smart TV",
                "brand": "Samsung",
                "price": 89999,
                "discount": 15,
                "shipping_fee": 1499,
                "qty": 40,
                "available": 28,
                "description": (
                    "<p>Crystal UHD 4K display with smart apps, HDR, and voice control "
                    "for a cinematic living-room experience.</p>"
                ),
                "specs": [("Resolution", "3840x2160"), ("HDR", "HDR10+"), ("OS", "Tizen")],
                "image": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1461151304267-38535e780c79?auto=format&fit=crop&w=800&q=80",
                ],
            },
        ],
    },
    {
        "category": "Fashion",
        "products": [
            {
                "name": "Classic Leather Crossbody Bag",
                "brand": "UrbanCraft",
                "price": 8999,
                "discount": 20,
                "shipping_fee": 249,
                "qty": 60,
                "available": 44,
                "description": (
                    "<p>Full-grain leather crossbody with adjustable strap, "
                    "interior zip pocket, and everyday city-ready style.</p>"
                ),
                "specs": [("Material", "Genuine leather"), ("Color", "Tan"), ("Closure", "Zip")],
                "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Men's Minimalist White Sneakers",
                "brand": "Stride",
                "price": 7499,
                "discount": 10,
                "shipping_fee": 199,
                "qty": 100,
                "available": 72,
                "description": (
                    "<p>Breathable knit upper, cushioned insole, and clean white design "
                    "that pairs with casual and smart-casual outfits.</p>"
                ),
                "specs": [("Upper", "Knit mesh"), ("Sole", "Rubber"), ("Fit", "True to size")],
                "image": "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Women's Cashmere Blend Scarf",
                "brand": "SoftThread",
                "price": 4599,
                "discount": 18,
                "shipping_fee": 149,
                "qty": 90,
                "available": 70,
                "description": (
                    "<p>Lightweight cashmere-blend scarf with soft hand-feel and "
                    "neutral tone for year-round layering.</p>"
                ),
                "specs": [("Material", "Cashmere blend"), ("Length", "180 cm"), ("Care", "Dry clean")],
                "image": "https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?auto=format&fit=crop&w=800&q=80",
                ],
            },
        ],
    },
    {
        "category": "Home & Kitchen",
        "products": [
            {
                "name": "Ceramic Pour-Over Coffee Set",
                "brand": "BrewHouse",
                "price": 5499,
                "discount": 14,
                "shipping_fee": 299,
                "qty": 70,
                "available": 55,
                "description": (
                    "<p>Matte ceramic dripper, matching mug, and reusable filter for "
                    "clean, café-style pour-over coffee at home.</p>"
                ),
                "specs": [("Pieces", "3"), ("Material", "Ceramic"), ("Capacity", "350 ml")],
                "image": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Non-Stick Cast Iron Skillet 10-Inch",
                "brand": "ForgeCook",
                "price": 6999,
                "discount": 11,
                "shipping_fee": 399,
                "qty": 50,
                "available": 35,
                "description": (
                    "<p>Pre-seasoned cast iron skillet for searing, baking, and "
                    "stovetop-to-oven cooking with even heat retention.</p>"
                ),
                "specs": [("Diameter", "10 inch"), ("Material", "Cast iron"), ("Oven safe", "260°C")],
                "image": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Aroma Diffuser with LED Light",
                "brand": "CalmAir",
                "price": 3999,
                "discount": 22,
                "shipping_fee": 199,
                "qty": 110,
                "available": 88,
                "description": (
                    "<p>Ultrasonic essential-oil diffuser with soft LED ambient light "
                    "and auto shut-off for bedrooms and offices.</p>"
                ),
                "specs": [("Tank", "300 ml"), ("Runtime", "8 hrs"), ("Modes", "Mist + Light")],
                "image": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=800&q=80",
                ],
            },
        ],
    },
    {
        "category": "Sports & Outdoors",
        "products": [
            {
                "name": "Insulated Stainless Water Bottle 1L",
                "brand": "TrailSip",
                "price": 2999,
                "discount": 16,
                "shipping_fee": 149,
                "qty": 150,
                "available": 120,
                "description": (
                    "<p>Double-wall vacuum insulation keeps drinks cold for 24 hours "
                    "or hot for 12 hours. Leak-proof lid included.</p>"
                ),
                "specs": [("Capacity", "1 L"), ("Material", "Stainless steel"), ("Insulation", "Vacuum")],
                "image": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Adjustable Dumbbell Set 20 kg",
                "brand": "IronFlex",
                "price": 18999,
                "discount": 13,
                "shipping_fee": 799,
                "qty": 35,
                "available": 22,
                "description": (
                    "<p>Space-saving adjustable dumbbells with secure dial system — "
                    "ideal for home strength training.</p>"
                ),
                "specs": [("Max weight", "20 kg"), ("Increments", "2 kg"), ("Grip", "Ergonomic")],
                "image": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1576678927484-cc907957088c?auto=format&fit=crop&w=800&q=80",
                ],
            },
            {
                "name": "Lightweight Hiking Daypack 25L",
                "brand": "PeakTrail",
                "price": 6499,
                "discount": 17,
                "shipping_fee": 249,
                "qty": 75,
                "available": 58,
                "description": (
                    "<p>Water-resistant daypack with padded straps, hydration sleeve, "
                    "and multiple organization pockets for day hikes.</p>"
                ),
                "specs": [("Capacity", "25 L"), ("Weight", "680 g"), ("Rain cover", "Included")],
                "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=800&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1501555088652-021faa106b9b?auto=format&fit=crop&w=800&q=80",
                ],
            },
        ],
    },
]

SLIDERS = [
    {
        "brand": "Sony Audio Week",
        "deal": "HOT DEALS",
        "sale": 30,
        "discount": 25,
        "link": "/product",
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1400&q=80",
    },
    {
        "brand": "Fresh Fashion Drops",
        "deal": "New Arraivels",
        "sale": 20,
        "discount": 18,
        "link": "/product",
        "image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1400&q=80",
    },
]

BANNERS = [
    {
        "deal": "Kitchen Essentials",
        "quote": "Cook better at home",
        "discount": 20,
        "image": "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=1000&q=80",
    },
    {
        "deal": "Outdoor Gear",
        "quote": "Ready for every trail",
        "discount": 15,
        "image": "https://images.unsplash.com/photo-1551632811-561732d1e306?auto=format&fit=crop&w=1000&q=80",
    },
]


class Command(BaseCommand):
    help = "Seed categories, products, sliders, and banners with images into MongoDB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing catalog data before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Clearing existing catalog...")
            Product_Image.objects.all().delete()
            Additional_Information.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            slider.objects.all().delete()
            banner_area.objects.all().delete()

        created_products = 0
        for group in SEED_CATALOG:
            category, _ = Category.objects.get_or_create(name=group["category"])
            for item in group["products"]:
                if Product.objects.filter(product_name=item["name"]).exists():
                    self.stdout.write(f"Skip existing: {item['name']}")
                    continue

                product = Product(
                    total_quantity=item["qty"],
                    Availability=item["available"],
                    product_name=item["name"],
                    price=item["price"],
                    Discount=item["discount"],
                    shipping_fee=item["shipping_fee"],
                    model_Name=item["brand"],
                    Categories=category,
                    Description=item["description"],
                )
                product.save()

                featured = self._download(item["image"], f"{product.slug or 'product'}-main")
                if featured:
                    product.featured_image.save(featured.name, featured, save=True)

                for index, url in enumerate(item.get("gallery", []), start=1):
                    gallery_file = self._download(url, f"{product.slug or 'product'}-g{index}")
                    if gallery_file:
                        image_row = Product_Image(product=product)
                        image_row.Image_url.save(gallery_file.name, gallery_file, save=True)

                for spec, detail in item.get("specs", []):
                    Additional_Information.objects.create(
                        product=product,
                        specification=spec,
                        detail=detail,
                    )

                created_products += 1
                self.stdout.write(self.style.SUCCESS(f"Created product: {product.product_name}"))

        for item in SLIDERS:
            if slider.objects.filter(Brand_Name=item["brand"]).exists():
                continue
            row = slider(
                Discount_Deal=item["deal"],
                SALE=item["sale"],
                Brand_Name=item["brand"],
                Discount=item["discount"],
                Link=item["link"],
            )
            image_file = self._download(item["image"], f"slider-{item['brand']}")
            if image_file:
                row.Image.save(image_file.name, image_file, save=True)
            else:
                row.save()
            self.stdout.write(self.style.SUCCESS(f"Created slider: {item['brand']}"))

        for item in BANNERS:
            if banner_area.objects.filter(Quote=item["quote"]).exists():
                continue
            row = banner_area(
                Discount_Deal=item["deal"],
                Quote=item["quote"],
                Discount=item["discount"],
            )
            image_file = self._download(item["image"], f"banner-{item['quote']}")
            if image_file:
                row.image.save(image_file.name, image_file, save=True)
            else:
                row.save()
            self.stdout.write(self.style.SUCCESS(f"Created banner: {item['quote']}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Products created: {created_products}. "
                f"Totals — categories: {Category.objects.count()}, "
                f"products: {Product.objects.count()}."
            )
        )

    def _download(self, url, basename):
        try:
            request = Request(url, headers={"User-Agent": "ShopAiSeed/1.0"})
            with urlopen(request, timeout=30) as response:
                data = response.read()
                content_type = response.headers.get_content_type()
        except Exception as exc:
            self.stderr.write(f"Image download failed ({url}): {exc}")
            return None

        ext = mimetypes.guess_extension(content_type) or Path(urlparse(url).path).suffix or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in basename).strip("-")
        filename = f"{safe_name}{ext}"
        return ContentFile(data, name=filename)
