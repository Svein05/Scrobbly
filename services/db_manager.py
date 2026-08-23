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
    async def set_user_session(discord_id: int, lastfm_username: str, session_key: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO users (discord_id, lastfm_username, session_key, scrobble_enabled)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(discord_id) DO UPDATE SET 
                    lastfm_username = excluded.lastfm_username,
                    session_key = excluded.session_key,
                    scrobble_enabled = 1
            ''', (discord_id, lastfm_username, session_key))
            await db.commit()

    @staticmethod
    async def get_user_data(discord_id: int) -> Optional[dict]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT discord_id, lastfm_username, session_key, scrobble_enabled FROM users WHERE discord_id = ?', (discord_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    @staticmethod
    async def set_scrobble_enabled(discord_id: int, enabled: bool) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('UPDATE users SET scrobble_enabled = ? WHERE discord_id = ?', (1 if enabled else 0, discord_id))
            await db.commit()

    @staticmethod
    async def get_active_scrobblers(discord_ids: list[int]) -> list[dict]:
        if not discord_ids:
            return []
        placeholders = ','.join('?' for _ in discord_ids)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f'''
                SELECT discord_id, lastfm_username, session_key 
                FROM users 
                WHERE discord_id IN ({placeholders}) 
                  AND session_key IS NOT NULL 
                  AND scrobble_enabled = 1
            ''', discord_ids) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    @staticmethod
    async def delete_user(discord_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('DELETE FROM users WHERE discord_id = ?', (discord_id,))
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def is_lastfm_linked(lastfm_username: str, exclude_discord_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT discord_id FROM users WHERE LOWER(lastfm_username) = LOWER(?) AND discord_id != ?', (lastfm_username, exclude_discord_id)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    @staticmethod
    async def get_guild_leaderboard(guild_id: int) -> Optional[tuple[int, int]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT leaderboard_channel_id, leaderboard_message_id FROM guild_settings WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    @staticmethod
    async def set_guild_leaderboard(guild_id: int, channel_id: int, message_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO guild_settings (guild_id, leaderboard_channel_id, leaderboard_message_id)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    leaderboard_channel_id = excluded.leaderboard_channel_id,
                    leaderboard_message_id = excluded.leaderboard_message_id
            ''', (guild_id, channel_id, message_id))
            await db.commit()

    @staticmethod
    async def get_all_users() -> list[tuple[int, str]]:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT discord_id, lastfm_username FROM users') as cursor:
                return await cursor.fetchall()
