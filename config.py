import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8000")

PRODUCT_NAME = "Nightstand with Hidden Drawer & Charging Station"
PRODUCT_DESCRIPTION = "Modern bedside table with hidden compartment, AC outlets, USB-A & USB-C ports"
PRODUCT_COLORS = ["Light Oak", "Black"]
PRODUCT_PRICE = int(os.getenv("PRODUCT_PRICE", "250"))   # USD, your selling price
SHIPPING_PRICE = int(os.getenv("SHIPPING_PRICE", "0"))   # 0 = free shipping included

DATABASE_PATH = "orders.db"
