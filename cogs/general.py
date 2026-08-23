import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Muestra la lista de comandos disponibles.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Centro de Ayuda de Scrobbly",
            description="Aquí tienes la lista completa de comandos organizados por categoría:",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="🎧 Last.fm & Scrobbling",
            value=(
                "• `/login`: **(Recomendado)** Vinculación web oficial con Last.fm para activar el Auto-Scrobble con `/play`.\n"
                "• `/link <username>`: Vinculación rápida de solo lectura.\n"
                "• `/np [usuario]`: Muestra la canción que tú o alguien más está escuchando.\n"
                "• `/scrobble <True/False>`: Activa o desactiva tu scrobbling automático en canales de voz.\n"
                "• `/unlink`: Desvincula tu cuenta y borra tus datos de la base de datos."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎶 Reproductor de Música (/play)",
            value=(
                "• `/play <canción/enlace>`: Reproduce música de YouTube, Spotify o SoundCloud.\n"
                "• `/pause` / `/resume`: Pausa o reanuda la canción actual.\n"
                "• `/skip`: Salta a la siguiente pista en la cola.\n"
                "• `/stop`: Detiene la reproducción, vacía la cola y desconecta el bot.\n"
                "• `/queue`: Muestra las próximas canciones en espera.\n"
                "• `/nowplaying_music`: Muestra la pista actual con barra de progreso y oyentes activos.\n"
                "• `/volume <1-150>`: Cambia el volumen del reproductor.\n"
                "• `/shuffle`: Mezcla la cola de reproducción aleatoriamente."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 Servidores & Leaderboards",
            value=(
                "• `/linkcanal <canal>`: *(Solo Admins)* Configura el canal de rankings semanales.\n"
                "• `/unlinkcanal`: *(Solo Admins)* Desvincula el canal de leaderboards."
            ),
            inline=False
        )
        
        embed.set_footer(text="Scrobbly • Música en Alta Definición & Last.fm Integration")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
