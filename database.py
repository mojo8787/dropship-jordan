import aiosqlite
from config import DATABASE_PATH


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_chat_id INTEGER NOT NULL,
                telegram_username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                color TEXT NOT NULL,
                product_price INTEGER NOT NULL,
                shipping_price INTEGER NOT NULL,
                stripe_session_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)
        await db.commit()


async def create_order(chat_id, username, full_name, phone, address, city, color, product_price, shipping_price):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (telegram_chat_id, telegram_username, full_name, phone, address, city, color, product_price, shipping_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, username, full_name, phone, address, city, color, product_price, shipping_price))
        await db.commit()
        return cursor.lastrowid


async def update_stripe_session(order_id, session_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE orders SET stripe_session_id = ? WHERE id = ?",
            (session_id, order_id)
        )
        await db.commit()


async def get_order_by_session(session_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE stripe_session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_order_paid(session_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = 'paid', paid_at = CURRENT_TIMESTAMP
            WHERE stripe_session_id = ?
        """, (session_id,))
        await db.commit()


async def get_all_orders():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
