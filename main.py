import discord
from discord.ext import commands
import asyncio
import logging

from config import config
from database import init_db

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

    async def on_ready(self):
        logger.info(f'Logueado exitosamente como {self.user} (ID: {self.user.id})')

if __name__ == '__main__':
    bot = LastFMBot()
    bot.run(config.discord_token)
