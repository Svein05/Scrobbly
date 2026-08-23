import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from services.db_manager import DBManager
from services.lastfm_client import LastFMClient, LastFMError

class AuthConfirmationView(discord.ui.View):
    def __init__(self, client: LastFMClient, token: str, auth_url: str, user_id: int):
        super().__init__(timeout=300)
        self.client = client
        self.token = token
        self.user_id = user_id
        
        # Botón 1: Redirección directa a Last.fm
        self.add_item(discord.ui.Button(
            label="1. Abrir Last.fm para Autorizar",
            style=discord.ButtonStyle.link,
            url=auth_url,
            emoji="🔗"
        ))

    @discord.ui.button(label="2. Ya lo autoricé (Confirmar)", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Esta ventana de autenticación pertenece a otro usuario.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            session_data = await self.client.get_session(self.token)
            username = session_data.get('name')
            session_key = session_data.get('key')

            if not username or not session_key:
                await interaction.followup.send("❌ No se pudo completar la autenticación. Asegúrate de hacer clic en 'Allow access' en la página de Last.fm antes de confirmar.", ephemeral=True)
                return

            # Verificar si otra cuenta de Discord ya tenía este username
            is_linked = await DBManager.is_lastfm_linked(username, interaction.user.id)
            if is_linked:
                await interaction.followup.send("❌ Esta cuenta de Last.fm ya está vinculada a otro usuario de Discord.", ephemeral=True)
                return

            # Guardar en DB con session_key y scrobbling activado
            await DBManager.set_user_session(interaction.user.id, username, session_key)

            # Obtener datos de perfil para feedback visual
            user_info = await self.client.get_user_info(username)
            avatar_url = user_info.get('image', [{}])[-1].get('#text', interaction.user.display_avatar.url)

            embed = discord.Embed(
                title="🎉 ¡Cuenta Vinculada con Éxito!",
                description=(
                    f"Tu cuenta de Discord ha sido vinculada oficialmente a **[{username}](https://www.last.fm/user/{username})** mediante Web Authentication.\n\n"
                    "✨ **Beneficios activados:**\n"
                    "• **Auto-Scrobble:** Tus canciones reproducidas con `/play` se registrarán automáticamente en tu perfil.\n"
                    "• **Now Playing en vivo:** Tu estado de Last.fm se actualizará mientras escuchas música en canales de voz.\n"
                    "• Consulta tus estadísticas con `/np`."
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=avatar_url)
            embed.set_footer(text="Sesión segura guardada • Puedes desactivar el auto-scrobble con /scrobble")

            # Deshabilitar botones una vez completado
            self.stop()
            await interaction.followup.send(embed=embed, ephemeral=True)

        except LastFMError as e:
            await interaction.followup.send(f"❌ Error al verificar sesión en Last.fm: {e}\n*(Asegúrate de haber aceptado los permisos en la página web)*", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error inesperado: {e}", ephemeral=True)

class LastFM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = LastFMClient()

    @app_commands.command(name="login", description="Vincula tu cuenta de Last.fm mediante la web oficial (permite auto-scrobbling con /play).")
    async def login(self, interaction: discord.Interaction):
        """Inicia el flujo seguro de autenticación Web (OAuth / Session Key)."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            token = await self.client.get_auth_token()
            auth_url = self.client.get_auth_url(token)
            
            embed = discord.Embed(
                title="🔐 Vinculación Oficial con Last.fm",
                description=(
                    "Para poder **hacer scrobbles automáticos** y actualizar tu estado cuando escuches música con el bot `/play`, "
                    "es necesario que autorices la aplicación de forma segura.\n\n"
                    "**Pasos:**\n"
                    "1️⃣ Haz clic en el botón **'1. Abrir Last.fm para Autorizar'** y presiona **'Allow Access'** en tu navegador.\n"
                    "2️⃣ Vuelve aquí y presiona **'2. Ya lo autoricé (Confirmar)'**."
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text="Este enlace de autorización expira en 5 minutos.")
            
            view = AuthConfirmationView(self.client, token, auth_url, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except LastFMError as e:
            await interaction.followup.send(f"❌ Error al iniciar autenticación con Last.fm: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ocurrió un error inesperado: {e}", ephemeral=True)

    @app_commands.command(name="scrobble", description="Activa o desactiva el scrobbling automático al escuchar música con el bot.")
    @app_commands.describe(activado="True para activar scrobble automático, False para desactivar")
    async def toggle_scrobble(self, interaction: discord.Interaction, activado: bool):
        await interaction.response.defer(ephemeral=True)
        
        user_data = await DBManager.get_user_data(interaction.user.id)
        if not user_data or not user_data.get('session_key'):
            await interaction.followup.send("❌ Para activar el scrobbling necesitas haber vinculado tu cuenta con `/login`.", ephemeral=True)
            return
            
        await DBManager.set_scrobble_enabled(interaction.user.id, activado)
        estado = "activado ✅" if activado else "desactivado ⏸️"
        await interaction.followup.send(f"Tu Auto-Scrobble ha sido **{estado}** para cuando escuches música con `/play`.", ephemeral=True)

    @app_commands.command(name="link", description="Vinculación rápida por nombre de usuario (solo lectura, sin scrobbling).")
    @app_commands.describe(username="Tu nombre de usuario en Last.fm")
    async def link(self, interaction: discord.Interaction, username: str):
        # Diferir respuesta porque consultamos una API externa
        await interaction.response.defer(ephemeral=True)
        
        try:
            is_linked = await DBManager.is_lastfm_linked(username, interaction.user.id)
            if is_linked:
                await interaction.followup.send("❌ Esa cuenta de Last.fm ya está vinculada a otro usuario de Discord.", ephemeral=True)
                return

            user_info = await self.client.get_user_info(username)
            if not user_info:
                await interaction.followup.send("❌ No se encontró ese usuario en Last.fm.", ephemeral=True)
                return
            
            real_username = user_info.get('name', username)
            
            await DBManager.set_user(interaction.user.id, real_username)
            await interaction.followup.send(
                f"✅ ¡Cuenta vinculada a **{real_username}**!\n"
                f"💡 *Nota:* Para activar el scrobbling automático de canciones con `/play`, te recomendamos usar **/login** para autorizar tu sesión.",
                ephemeral=True
            )
            
        except LastFMError as e:
            await interaction.followup.send(f"❌ Error de Last.fm: {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("❌ Ocurrió un error inesperado al vincular tu cuenta.", ephemeral=True)

    @app_commands.command(name="np", description="Muestra la canción que estás escuchando actualmente.")
    @app_commands.describe(usuario="Usuario del servidor (opcional)")
    async def now_playing(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        target_user = usuario or interaction.user
        
        await interaction.response.defer()
        
        lastfm_username = await DBManager.get_user(target_user.id)
        if not lastfm_username:
            msg = f"{'No tienes' if target_user == interaction.user else f'{target_user.display_name} no tiene'} una cuenta de Last.fm vinculada. Usa `/login` o `/link <username>`."
            await interaction.followup.send(msg)
            return
            
        try:
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
            
            images = track.get('image', [])
            image_url = images[-1].get('#text') if images else ''
            
            is_now_playing = track.get('@attr', {}).get('nowplaying') == 'true'
            total_scrobbles = user_info.get('playcount', '0')
            
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

    @app_commands.command(name="unlink", description="Desvincula tu cuenta de Last.fm del bot.")
    async def unlink(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        deleted = await DBManager.delete_user(interaction.user.id)
        
        if deleted:
            await interaction.followup.send("✅ Tu cuenta de Last.fm ha sido desvinculada exitosamente. Tus datos han sido borrados de nuestra base de datos.", ephemeral=True)
        else:
            await interaction.followup.send("❌ No tenías ninguna cuenta vinculada previamente.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(LastFM(bot))
