import os
import databases

DATABASE_URL = os.getenv("DATABASE_URL")

database = databases.Database(DATABASE_URL)

async def create_tables():
    await database.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        credits INTEGER DEFAULT 0,
        roles TEXT[],
        last_farm TEXT
    );
    """)

async def get_user(user_id):
    query = "SELECT * FROM users WHERE user_id = :user_id"
    user = await database.fetch_one(query, values={"user_id": user_id})
    if user:
        return {
            "credits": user["credits"],
            "roles": user["roles"] or [],
            "last_farm": user["last_farm"]
        }
    else:
        await database.execute("""
            INSERT INTO users (user_id, credits, roles, last_farm)
            VALUES (:user_id, 0, ARRAY[]::TEXT[], NULL)
        """, values={"user_id": user_id})
        return {"credits": 0, "roles": [], "last_farm": None}

async def update_user(user_id, credits, roles, last_farm):
    query = """
    UPDATE users
    SET credits = :credits,
        roles = :roles,
        last_farm = :last_farm
    WHERE user_id = :user_id
    """
    await database.execute(query, values={
        "user_id": user_id,
        "credits": credits,
        "roles": roles,
        "last_farm": last_farm
    })
