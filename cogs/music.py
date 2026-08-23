import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import time
import logging
from typing import Optional, List, Dict, Any

from config import config
from services.db_manager import DBManager
from services.lastfm_client import LastFMClient, LastFMError

logger = logging.getLogger('music')

def format_duration(milliseconds: int) -> str:
    seconds = int(milliseconds // 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

class MusicControlsView(discord.ui.View):
    def __init__(self, cog: "Music", guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music_pause_resume")
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message("❌ No hay ninguna canción reproduciéndose.", ephemeral=True)
            return

        await player.pause(not player.paused)
        estado = "Pausado ⏸️" if player.paused else "Reanudado ▶️"
        await interaction.response.send_message(f"🎵 Reproductor {estado}.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message("❌ No hay ninguna canción reproduciéndose.", ephemeral=True)
            return

        await player.skip(force=True)
        await interaction.response.send_message("⏭️ Canción saltada.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message("❌ El bot no está en un canal de voz.", ephemeral=True)
            return

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message("⏹️ Reproducción detenida y cola vaciada.", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.lastfm_client = LastFMClient()
        # Almacena tareas de scrobble pendientes por guild_id: {guild_id: asyncio.Task}
        self.scrobble_tasks: Dict[int, asyncio.Task] = {}
        # Estado de inicio de canción por guild_id: {guild_id: {'track': Track, 'start_time': int, 'scrobbled_users': set()}}
        self.playback_context: Dict[int, Dict[str, Any]] = {}

    async def cog_load(self):
        """Conecta con el nodo de Lavalink al cargar el Cog."""
        try:
            nodes = [
                wavelink.Node(
                    uri=config.lavalink_uri,
                    password=config.lavalink_password,
                    inactive_player_timeout=300
                )
            ]
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            logger.info("Intentando conectar con el nodo de Lavalink...")
        except Exception as e:
            logger.error(f"Fallo al conectar con Lavalink: {e}")

    # --- Listeners de Eventos de Wavelink ---

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ Nodo Lavalink conectado exitosamente: {payload.node!r}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = payload.track
        if not player or not player.guild:
            return

        guild_id = player.guild.id
        now_ts = int(time.time())

        # Cancelar tarea previa si existiera
        if guild_id in self.scrobble_tasks and not self.scrobble_tasks[guild_id].done():
            self.scrobble_tasks[guild_id].cancel()

        # Identificar oyentes en el canal de voz
        listeners = [
            member.id for member in player.channel.members 
            if not member.bot and not member.voice.self_deaf and not member.voice.deaf
        ] if player.channel else []

        self.playback_context[guild_id] = {
            'track': track,
            'start_time': now_ts,
            'scrobbled_users': set(),
            'listeners': listeners
        }

        # 1. Enviar "Now Playing" a Last.fm
        asyncio.create_task(self._broadcast_now_playing(guild_id, track, listeners))

        # 2. Programar Auto-Scrobble al 50% de duración o 4 minutos
        duration_sec = (track.length / 1000) if track.length else 180
        # Regla estándar de Last.fm: min(duration / 2, 240 segundos), mínimo 30 segundos
        scrobble_delay = max(30, min(duration_sec / 2, 240))

        task = asyncio.create_task(self._scheduled_scrobble(guild_id, track, scrobble_delay))
        self.scrobble_tasks[guild_id] = task

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player or not player.guild:
            return

        guild_id = player.guild.id
        # Limpieza de tareas
        if guild_id in self.scrobble_tasks:
            task = self.scrobble_tasks.pop(guild_id, None)
            if task and not task.done():
                task.cancel()

    # --- Lógica de Scrobbling Asíncrono ---

    async def _broadcast_now_playing(self, guild_id: int, track: wavelink.Playable, listener_ids: List[int]):
        """Notifica 'Now Playing' a Last.fm para todos los miembros autorizados en el canal de voz."""
        if not listener_ids:
            return

        try:
            scrobblers = await DBManager.get_active_scrobblers(listener_ids)
            if not scrobblers:
                return

            artist = getattr(track, 'author', 'Artista Desconocido')
            title = getattr(track, 'title', 'Canción Desconocida')
            album = getattr(track, 'album', None)
            duration = int(track.length // 1000) if track.length else None

            tasks = []
            for user in scrobblers:
                tasks.append(
                    self.lastfm_client.update_now_playing(
                        artist=artist,
                        track=title,
                        session_key=user['session_key'],
                        album=album.name if album and hasattr(album, 'name') else None,
                        duration=duration
                    )
                )
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, user in zip(results, scrobblers):
                if isinstance(res, Exception):
                    logger.warning(f"No se pudo actualizar Now Playing para {user['lastfm_username']}: {res}")
                else:
                    logger.info(f"Now Playing actualizado en Last.fm para {user['lastfm_username']}: {artist} - {title}")
        except Exception as e:
            logger.error(f"Error en broadcast_now_playing: {e}")

    async def _scheduled_scrobble(self, guild_id: int, track: wavelink.Playable, delay: float):
        """Espera el umbral de reproducción y envía el scrobble oficial."""
        try:
            await asyncio.sleep(delay)
            context = self.playback_context.get(guild_id)
            if not context or context.get('track') != track:
                return

            listeners = context.get('listeners', [])
            if not listeners:
                return

            scrobblers = await DBManager.get_active_scrobblers(listeners)
            if not scrobblers:
                return

            artist = getattr(track, 'author', 'Artista Desconocido')
            title = getattr(track, 'title', 'Canción Desconocida')
            album = getattr(track, 'album', None)
            start_ts = context.get('start_time', int(time.time()))

            tasks = []
            for user in scrobblers:
                tasks.append(
                    self.lastfm_client.scrobble(
                        artist=artist,
                        track=title,
                        timestamp=start_ts,
                        session_key=user['session_key'],
                        album=album.name if album and hasattr(album, 'name') else None
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, user in zip(results, scrobblers):
                if isinstance(res, Exception):
                    logger.warning(f"Error enviando scrobble a {user['lastfm_username']}: {res}")
                else:
                    logger.info(f"🎉 Scrobble enviado exitosamente a Last.fm para {user['lastfm_username']}: {artist} - {title}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error en scheduled_scrobble: {e}")

    # --- Comandos de Barra (Slash Commands) ---

    @app_commands.command(name="play", description="Reproduce música de YouTube, Spotify o SoundCloud en tu canal de voz.")
    @app_commands.describe(busqueda="Nombre de la canción, artista o enlace (YouTube, Spotify, SoundCloud)")
    async def play(self, interaction: discord.Interaction, busqueda: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Debes estar en un canal de voz para reproducir música.", ephemeral=True)
            return

        await interaction.response.defer()

        # Obtener o conectar el reproductor
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                await interaction.followup.send(f"❌ Error al conectar al canal de voz: {e}")
                return
        elif player.channel != interaction.user.voice.channel:
            await player.move_to(interaction.user.voice.channel)

        # Buscar canciones
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(busqueda)
        except Exception as e:
            await interaction.followup.send(f"❌ Error buscando pistas en Lavalink: {e}")
            return

        if not tracks:
            await interaction.followup.send(f"❌ No se encontraron resultados para: `{busqueda}`")
            return

        view = MusicControlsView(self, interaction.guild_id)

        # Si es una playlist
        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            embed = discord.Embed(
                title="📑 Playlist Añadida a la Cola",
                description=f"**[{tracks.name}]({busqueda})**\nSe añadieron **{added}** canciones a la lista.",
                color=discord.Color.red()
            )
            if tracks.artwork:
                embed.set_thumbnail(url=tracks.artwork)
            await interaction.followup.send(embed=embed, view=view)
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            
            dur = format_duration(track.length) if track.length else "En vivo"
            
            if not player.playing:
                embed = discord.Embed(
                    title="🎶 Reproduciendo Ahora",
                    description=f"**[{track.title}]({track.uri})**\nPor: **{track.author}**",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="⏳ Añadida a la Cola",
                    description=f"**[{track.title}]({track.uri})**\nPor: **{track.author}**\nPosición en cola: **#{len(player.queue)}**",
                    color=discord.Color.dark_red()
                )
                
            embed.add_field(name="Duración", value=dur, inline=True)
            embed.add_field(name="Solicitado por", value=interaction.user.mention, inline=True)
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
                
            embed.set_footer(text="Auto-Scrobble activo para oyentes con Last.fm vinculado")
            await interaction.followup.send(embed=embed, view=view)

        # Si no estaba reproduciendo, iniciar
        if not player.playing:
            await player.play(player.queue.get(), volume=100)

    @app_commands.command(name="pause", description="Pausa la reproducción actual.")
    async def pause(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message("❌ No hay nada reproduciéndose actualmente.", ephemeral=True)
            return

        await player.pause(True)
        await interaction.response.send_message("⏸️ Música pausada.")

    @app_commands.command(name="resume", description="Reanuda la reproducción pausada.")
    async def resume(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message("❌ No hay reproductor activo en este servidor.", ephemeral=True)
            return

        await player.pause(False)
        await interaction.response.send_message("▶️ Música reanudada.")

    @app_commands.command(name="skip", description="Salta a la siguiente canción en la cola.")
    async def skip(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message("❌ No hay canciones para saltar.", ephemeral=True)
            return

        current_title = player.current.title if player.current else "canción actual"
        await player.skip(force=True)
        await interaction.response.send_message(f"⏭️ Se ha saltado: **{current_title}**")

    @app_commands.command(name="stop", description="Detiene la música, vacía la cola y desconecta al bot.")
    async def stop(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message("❌ El bot no está en un canal de voz.", ephemeral=True)
            return

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message("⏹️ Reproducción terminada y bot desconectado.")

    @app_commands.command(name="queue", description="Muestra la lista de canciones en cola.")
    async def queue_cmd(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            await interaction.response.send_message("❌ La cola de reproducción está vacía.", ephemeral=True)
            return

        embed = discord.Embed(title="🎶 Cola de Reproducción", color=discord.Color.red())

        if player.current:
            pos = format_duration(player.position)
            dur = format_duration(player.current.length) if player.current.length else "En vivo"
            embed.add_field(
                name="🔊 En reproducción:",
                value=f"**[{player.current.title}]({player.current.uri})**\n`{pos} / {dur}` | Por: {player.current.author}",
                inline=False
            )

        if not player.queue.is_empty:
            queue_list = []
            for i, track in enumerate(player.queue[:10], start=1):
                dur = format_duration(track.length) if track.length else "En vivo"
                queue_list.append(f"`{i}.` **[{track.title}]({track.uri})** ({dur}) - *{track.author}*")
            
            queue_text = "\n".join(queue_list)
            if len(player.queue) > 10:
                queue_text += f"\n\n*... y {len(player.queue) - 10} canciones más.*"
            embed.add_field(name="Próximas en cola:", value=queue_text, inline=False)
        else:
            embed.add_field(name="Próximas en cola:", value="*No hay más canciones en espera.*", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying_music", description="Muestra detalles avanzados de la canción que suena y los oyentes con scrobble activo.")
    async def nowplaying_music(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or not player.current:
            await interaction.response.send_message("❌ No hay música reproduciéndose en este momento.", ephemeral=True)
            return

        track = player.current
        pos = format_duration(player.position)
        dur = format_duration(track.length) if track.length else "En vivo"

        # Barra de progreso visual
        if track.length and track.length > 0:
            percent = min(1.0, player.position / track.length)
            bars = int(percent * 15)
            progress_bar = "▬" * bars + "🔘" + "▬" * (15 - bars)
        else:
            progress_bar = "🔴 En vivo"

        embed = discord.Embed(
            title=track.title,
            url=track.uri,
            description=f"**{track.author}**\n\n`{pos}` {progress_bar} `{dur}`",
            color=discord.Color.red()
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        # Mostrar oyentes del canal con scrobble activo
        if player.channel:
            listeners = [m.id for m in player.channel.members if not m.bot]
            scrobblers = await DBManager.get_active_scrobblers(listeners)
            if scrobblers:
                users_str = ", ".join([f"[{u['lastfm_username']}](https://www.last.fm/user/{u['lastfm_username']})" for u in scrobblers])
                embed.add_field(name="🎧 Oyentes Scrobbleando en Last.fm:", value=users_str, inline=False)

        view = MusicControlsView(self, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="volume", description="Ajusta el volumen de la música (1 a 150%).")
    @app_commands.describe(nivel="Porcentaje de volumen (1-150)")
    async def volume(self, interaction: discord.Interaction, nivel: app_commands.Range[int, 1, 150]):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message("❌ No hay reproductor activo en este momento.", ephemeral=True)
            return

        await player.set_volume(nivel)
        await interaction.response.send_message(f"🔊 Volumen ajustado a **{nivel}%**.")

    @app_commands.command(name="shuffle", description="Mezcla aleatoriamente las canciones de la cola.")
    async def shuffle(self, interaction: discord.Interaction):
        player: Optional[wavelink.Player] = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            await interaction.response.send_message("❌ La cola está vacía o solo tiene una canción.", ephemeral=True)
            return

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Cola de reproducción mezclada aleatoriamente.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
