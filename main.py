import discord
from discord.ext import commands, tasks
import asyncio
import logging
import json
import os
import aiosqlite

from config import config
from database import init_db, DB_PATH

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot')

class LastFMBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # Requerido para leer miembros en leaderboards
        
        super().__init__(
            command_prefix=commands.when_mentioned, # Usaremos principalmente slash commands
            intents=intents,
            help_command=None # Deshabilitamos el help por defecto para crear el nuestro
        )
        
        self.initial_extensions = [
            'cogs.general',
            'cogs.lastfm',
            'cogs.leaderboard'
        ]

    async def setup_hook(self):
        logger.info("Inicializando Base de Datos...")
        await init_db()
        
        logger.info("Cargando extensiones (Cogs)...")
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Extensión {ext} cargada.")
            except Exception as e:
                logger.error(f"Fallo al cargar extensión {ext}: {e}")
                
        logger.info("Sincronizando comandos de barra (Slash Commands)...")
        await self.tree.sync()
        logger.info("Comandos sincronizados.")
        
        self.save_stats_loop.start()
        logger.info("Ciclo de guardado de stats iniciado.")

    @tasks.loop(minutes=5)
    async def save_stats_loop(self):
        await self.wait_until_ready()
        
        # 1. Servidores
        servers = len(self.guilds)
        
        # 2. Usuarios Registrados (en la base de datos)
        registered_users = 0
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                    row = await cursor.fetchone()
                    if row:
                        registered_users = row[0]
        except Exception as e:
            logger.error(f"Error contando usuarios en DB: {e}")
        
        stats = {
            "servers": servers,
            "users": registered_users
        }
        
        # Guardar en el directorio website
        filepath = os.path.join(os.path.dirname(__file__), "website", "stats.json")
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(stats, f)
            logger.info("Stats guardadas en website/stats.json")
        except Exception as e:
            logger.error(f"Fallo al guardar stats: {e}")

    async def on_ready(self):
        logger.info(f'Logueado exitosamente como {self.user} (ID: {self.user.id})')

if __name__ == '__main__':
    bot = LastFMBot()
    bot.run(config.discord_token)
