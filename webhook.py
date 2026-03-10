import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from telegram import Bot

import config
import database

stripe.api_key = config.STRIPE_SECRET_KEY

app = FastAPI()
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


@app.on_event("startup")
async def startup():
    await database.init_db()


# ─── Stripe webhook ───────────────────────────────────────────────────────────

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        chat_id = int(session["metadata"]["telegram_chat_id"])
        order_id = session["metadata"]["order_id"]

        await database.mark_order_paid(session_id)
        order = await database.get_order_by_session(session_id)

        # Notify customer
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"✅ *Payment confirmed!*\n\n"
                f"Thank you {order['full_name']}!\n"
                f"Your order #{order_id} has been received.\n\n"
                f"📦 We will ship your *{order['color']}* nightstand to:\n"
                f"📍 {order['city']}, {order['address']}\n\n"
                f"We'll send you tracking info soon. 🚚"
            ),
            parse_mode="Markdown"
        )

        # Notify owner
        await bot.send_message(
            chat_id=config.TELEGRAM_OWNER_ID,
            text=(
                f"💰 *NEW PAID ORDER #{order_id}*\n\n"
                f"👤 {order['full_name']}\n"
                f"📞 {order['phone']}\n"
                f"📍 {order['city']}, {order['address']}\n"
                f"🎨 Color: {order['color']}\n"
                f"💵 Amount: ${order['product_price']} USD\n\n"
                f"⚡ Place the supplier order now!"
            ),
            parse_mode="Markdown"
        )

    return {"status": "ok"}


# ─── Success / Cancel pages ───────────────────────────────────────────────────

@app.get("/success")
async def success_page():
    return HTMLResponse("""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#f0fff4">
    <h1 style="color:#22c55e">✅ Payment Successful!</h1>
    <p>Your order has been confirmed. Go back to Telegram for details.</p>
    </body></html>
    """)


@app.get("/cancel")
async def cancel_page():
    return HTMLResponse("""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#fff0f0">
    <h1 style="color:#ef4444">❌ Payment Cancelled</h1>
    <p>Your order was not completed. Go back to Telegram to try again.</p>
    </body></html>
    """)


# ─── Serve landing page ───────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory="static", html=True), name="static")
