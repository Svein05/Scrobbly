import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'bot.db')

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabla de usuarios
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                discord_id INTEGER PRIMARY KEY,
                lastfm_username TEXT NOT NULL,
                session_key TEXT,
                scrobble_enabled INTEGER DEFAULT 1,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de configuración de servidores
        await db.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                leaderboard_channel_id INTEGER,
                leaderboard_message_id INTEGER
            )
        ''')
        
        # Migraciones: Intentar añadir columnas si la tabla ya existía de antes
        try:
            await db.execute('ALTER TABLE guild_settings ADD COLUMN leaderboard_message_id INTEGER')
        except aiosqlite.OperationalError:
            pass # La columna ya existe
            
        try:
            await db.execute('ALTER TABLE users ADD COLUMN session_key TEXT')
        except aiosqlite.OperationalError:
            pass
            
        try:
            await db.execute('ALTER TABLE users ADD COLUMN scrobble_enabled INTEGER DEFAULT 1')
        except aiosqlite.OperationalError:
            pass
            
        await db.commit()
