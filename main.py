import asyncio
import uvicorn
from telegram.ext import ApplicationBuilder

import database
from bot import build_bot
from webhook import app as fastapi_app
import config


async def run_bot(bot_app):
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    print("✅ Telegram bot started")


async def run_server():
    cfg = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(cfg)
    print("✅ Web server started on port 8000")
    await server.serve()


async def main():
    await database.init_db()
    print("✅ Database ready")

    bot_app = build_bot()

    await asyncio.gather(
        run_bot(bot_app),
        run_server()
    )


if __name__ == "__main__":
    asyncio.run(main())
