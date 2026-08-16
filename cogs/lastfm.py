import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from services.db_manager import DBManager
from services.lastfm_client import LastFMClient, LastFMError

class LastFM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = LastFMClient()

    @app_commands.command(name="link", description="Vincula tu cuenta de Discord con tu usuario de Last.fm.")
    @app_commands.describe(username="Tu nombre de usuario en Last.fm")
    async def link(self, interaction: discord.Interaction, username: str):
        # Diferir respuesta porque consultamos una API externa
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validamos que el usuario existe en Last.fm
            user_info = await self.client.get_user_info(username)
            if not user_info:
                await interaction.followup.send("❌ No se encontró ese usuario en Last.fm.", ephemeral=True)
                return
            
            # Guardamos en DB
            await DBManager.set_user(interaction.user.id, username)
            await interaction.followup.send(f"✅ ¡Cuenta vinculada exitosamente a **{username}**!", ephemeral=True)
            
        except LastFMError as e:
            await interaction.followup.send(f"❌ Error de Last.fm: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("❌ Ocurrió un error inesperado al vincular tu cuenta.", ephemeral=True)

    @app_commands.command(name="np", description="Muestra la canción que estás escuchando actualmente.")
    @app_commands.describe(usuario="Usuario del servidor (opcional)")
    async def now_playing(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        target_user = usuario or interaction.user
        
        # Diferimos porque vamos a hacer requests a DB y a Last.fm
        await interaction.response.defer()
        
        lastfm_username = await DBManager.get_user(target_user.id)
        if not lastfm_username:
            msg = f"{'No tienes' if target_user == interaction.user else f'{target_user.display_name} no tiene'} una cuenta de Last.fm vinculada. Usa `/link <username>`."
            await interaction.followup.send(msg)
            return
            
        try:
            # Obtener datos en paralelo o secuencialmente
            user_info = await self.client.get_user_info(lastfm_username)
            recent_tracks = await self.client.get_recent_tracks(lastfm_username)
            
            if not recent_tracks:
                await interaction.followup.send(f"❌ No se encontraron reproducciones recientes para **{lastfm_username}**.")
                return
                
            track = recent_tracks[0]
            
            artist = track.get('artist', {}).get('#text', 'Artista Desconocido')
            name = track.get('name', 'Canción Desconocida')
            album = track.get('album', {}).get('#text', '')
            url = track.get('url', '')
            
            # Imágenes vienen en un array, usamos la extragrande o la última disponible
            images = track.get('image', [])
            image_url = images[-1].get('#text') if images else ''
            
            # Verificar si está escuchando ahora
            is_now_playing = track.get('@attr', {}).get('nowplaying') == 'true'
            
            total_scrobbles = user_info.get('playcount', '0')
            
            # Construir Embed
            status = "Escuchando ahora" if is_now_playing else "Última canción"
            embed = discord.Embed(
                title=name,
                url=url,
                description=f"**{artist}**\n*{album}*" if album else f"**{artist}**",
                color=discord.Color.red()
            )
            
            embed.set_author(name=f"{lastfm_username} - {status}", icon_url=target_user.display_avatar.url, url=f"https://www.last.fm/user/{lastfm_username}")
            if image_url:
                embed.set_thumbnail(url=image_url)
                
            embed.set_footer(text=f"Total Scrobbles: {total_scrobbles}")
            
            await interaction.followup.send(embed=embed)
            
        except LastFMError as e:
            await interaction.followup.send(f"❌ Error de Last.fm: {e}")
        except Exception as e:
            await interaction.followup.send(f"❌ Ocurrió un error inesperado.")

async def setup(bot: commands.Bot):
    await bot.add_cog(LastFM(bot))
