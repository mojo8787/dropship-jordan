import stripe
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

import config
import database

stripe.api_key = config.STRIPE_SECRET_KEY

# Conversation states
NAME, PHONE, CITY, ADDRESS, COLOR, CONFIRM = range(6)


# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Order Now", callback_data="order")]]
    await update.message.reply_photo(
        photo="https://m.media-amazon.com/images/I/71Z5QpEIBNL._AC_SL1500_.jpg",
        caption=(
            f"*{config.PRODUCT_NAME}*\n\n"
            f"{config.PRODUCT_DESCRIPTION}\n\n"
            f"✅ Hidden magnetic compartment\n"
            f"✅ AC outlet + USB-A + USB-C charging\n"
            f"✅ Free delivery to Jordan\n\n"
            f"💰 *${config.PRODUCT_PRICE} USD*"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Order flow ───────────────────────────────────────────────────────────────

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Great! Let's set up your order.\n\n👤 What is your *full name*?",
        parse_mode="Markdown"
    )
    return NAME


async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text("📞 Your *phone number* (with country code, e.g. +962...):", parse_mode="Markdown")
    return PHONE


async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("🏙️ Which *city* in Jordan?", parse_mode="Markdown")
    return CITY


async def get_city(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["city"] = update.message.text.strip()
    await update.message.reply_text("🏠 Your *full delivery address*:", parse_mode="Markdown")
    return ADDRESS


async def get_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["address"] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton(c, callback_data=f"color_{c}")] for c in config.PRODUCT_COLORS]
    await update.message.reply_text(
        "🎨 Choose your color:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COLOR


async def get_color(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    color = update.callback_query.data.replace("color_", "")
    ctx.user_data["color"] = color

    total = config.PRODUCT_PRICE + config.SHIPPING_PRICE
    shipping_text = "Free" if config.SHIPPING_PRICE == 0 else f"${config.SHIPPING_PRICE}"

    summary = (
        f"📋 *Order Summary*\n\n"
        f"📦 Product: {config.PRODUCT_NAME}\n"
        f"🎨 Color: {color}\n"
        f"👤 Name: {ctx.user_data['full_name']}\n"
        f"📞 Phone: {ctx.user_data['phone']}\n"
        f"📍 City: {ctx.user_data['city']}\n"
        f"🏠 Address: {ctx.user_data['address']}\n\n"
        f"💰 Price: ${config.PRODUCT_PRICE}\n"
        f"🚚 Shipping: {shipping_text}\n"
        f"━━━━━━━━━━━━━\n"
        f"💳 *Total: ${total} USD*"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Pay", callback_data="confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    await update.callback_query.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM


async def confirm_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    if update.callback_query.data == "cancel":
        await update.callback_query.message.reply_text("Order cancelled. Type /start to begin again.")
        return ConversationHandler.END

    user = update.callback_query.from_user
    total = config.PRODUCT_PRICE + config.SHIPPING_PRICE

    # Save order to DB
    order_id = await database.create_order(
        chat_id=user.id,
        username=user.username,
        full_name=ctx.user_data["full_name"],
        phone=ctx.user_data["phone"],
        address=ctx.user_data["address"],
        city=ctx.user_data["city"],
        color=ctx.user_data["color"],
        product_price=config.PRODUCT_PRICE,
        shipping_price=config.SHIPPING_PRICE
    )

    # Create Stripe checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"{config.PRODUCT_NAME} ({ctx.user_data['color']})",
                    "description": f"Delivery to: {ctx.user_data['city']}, Jordan"
                },
                "unit_amount": total * 100,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{config.WEBHOOK_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{config.WEBHOOK_URL}/cancel",
        metadata={
            "order_id": str(order_id),
            "telegram_chat_id": str(user.id),
        }
    )

    await database.update_stripe_session(order_id, session.id)

    await update.callback_query.message.reply_text(
        f"🔐 *Secure payment link ready!*\n\n"
        f"Click below to complete your purchase:\n\n"
        f"👉 [Pay ${total} USD]({session.url})\n\n"
        f"_Your order #{order_id} will be confirmed after payment._",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Type /start to begin again.")
    return ConversationHandler.END


# ─── Owner: /orders ───────────────────────────────────────────────────────────

async def list_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.TELEGRAM_OWNER_ID:
        return

    orders = await database.get_all_orders()
    if not orders:
        await update.message.reply_text("No orders yet.")
        return

    text = "📦 *All Orders*\n\n"
    for o in orders:
        status_icon = "✅" if o["status"] == "paid" else "⏳"
        text += (
            f"{status_icon} Order #{o['id']} — *{o['status'].upper()}*\n"
            f"👤 {o['full_name']} | {o['phone']}\n"
            f"📍 {o['city']}, {o['address']}\n"
            f"🎨 {o['color']} | 💰 ${o['product_price']}\n"
            f"🕐 {o['created_at']}\n\n"
        )

    # Telegram messages max 4096 chars
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000], parse_mode="Markdown")


# ─── Build app ────────────────────────────────────────────────────────────────

def build_bot():
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern="^order$")],
        states={
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CITY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            COLOR:   [CallbackQueryHandler(get_color, pattern="^color_")],
            CONFIRM: [CallbackQueryHandler(confirm_order, pattern="^(confirm|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", list_orders))
    app.add_handler(conv)

    return app
