import asyncio
import uvicorn
from webhook import app as fastapi_app
import database


async def main():
    await database.init_db()
    cfg = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(cfg)
    print("✅ Server starting on port 8000")
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
