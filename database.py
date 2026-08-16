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
        
        # Migración: Intentar añadir la columna si la tabla ya existía de antes
        try:
            await db.execute('ALTER TABLE guild_settings ADD COLUMN leaderboard_message_id INTEGER')
        except aiosqlite.OperationalError:
            pass # La columna ya existe
            
        await db.commit()
