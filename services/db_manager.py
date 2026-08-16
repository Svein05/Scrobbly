import aiosqlite
from database import DB_PATH
from typing import Optional

class DBManager:
    @staticmethod
    async def get_user(discord_id: int) -> Optional[str]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT lastfm_username FROM users WHERE discord_id = ?', (discord_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    @staticmethod
    async def set_user(discord_id: int, lastfm_username: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO users (discord_id, lastfm_username)
                VALUES (?, ?)
                ON CONFLICT(discord_id) DO UPDATE SET lastfm_username = excluded.lastfm_username
            ''', (discord_id, lastfm_username))
            await db.commit()

    @staticmethod
    async def get_guild_leaderboard_channel(guild_id: int) -> Optional[int]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT leaderboard_channel_id FROM guild_settings WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    @staticmethod
    async def set_guild_leaderboard_channel(guild_id: int, channel_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO guild_settings (guild_id, leaderboard_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET leaderboard_channel_id = excluded.leaderboard_channel_id
            ''', (guild_id, channel_id))
            await db.commit()

    @staticmethod
    async def get_all_users() -> list[tuple[int, str]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT discord_id, lastfm_username FROM users') as cursor:
                return await cursor.fetchall()
