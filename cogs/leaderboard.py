import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import io
import aiohttp
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

from services.db_manager import DBManager
from services.lastfm_client import LastFMClient

class ConfirmView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.value = None
        self.author_id = author_id

    @discord.ui.button(label="Sí, cambiar canal", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
        self.value = True
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
        self.value = False
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = LastFMClient()
        self.leaderboard_task.start()

    def cog_unload(self):
        self.leaderboard_task.cancel()

    @app_commands.command(name="linkcanal", description="Configura el canal para enviar Leaderboards automáticos.")
    @app_commands.describe(canal="Canal de texto o anuncios")
    @app_commands.default_permissions(manage_guild=True)
    async def link_canal(self, interaction: discord.Interaction, canal: discord.abc.GuildChannel):
        if not hasattr(canal, 'send'):
            await interaction.response.send_message("❌ Debes seleccionar un canal de texto válido.", ephemeral=True)
            return
            
        existing_lb = await DBManager.get_guild_leaderboard(interaction.guild_id)
        if existing_lb and existing_lb[0] != canal.id:
            view = ConfirmView(interaction.user.id)
            old_canal = interaction.guild.get_channel(existing_lb[0])
            old_canal_mention = old_canal.mention if old_canal else "un canal desconocido"
            await interaction.response.send_message(f"⚠️ El servidor ya tiene configurado el canal {old_canal_mention} para el Leaderboard. ¿Seguro que quieres cambiarlo a {canal.mention}?", view=view, ephemeral=True)
            
            await view.wait()
            if view.value is None:
                return await interaction.edit_original_response(content="⏳ Tiempo de espera agotado. Configuración cancelada.")
            if not view.value:
                return await interaction.edit_original_response(content="❌ Acción cancelada.")
        else:
            await interaction.response.defer(ephemeral=True)
            
        embed, file = await self.generate_leaderboard_data(interaction.guild)
        if not embed:
            embed = discord.Embed(
                title=f"🏆 TOP 10 Scrobbles - {interaction.guild.name}",
                description="No hay suficientes usuarios vinculados aún. Usa `/link` para participar.",
                color=discord.Color.red()
            )
            file = None
            
        try:
            kwargs = {'embed': embed}
            if file:
                kwargs['file'] = file
                
            msg = await canal.send(**kwargs)
            await DBManager.set_guild_leaderboard(interaction.guild_id, canal.id, msg.id)
            
            if interaction.response.is_done():
                await interaction.edit_original_response(content=f"✅ El canal {canal.mention} ha sido configurado. El Leaderboard se actualizará automáticamente allí.")
            else:
                await interaction.followup.send(f"✅ El canal {canal.mention} ha sido configurado. El Leaderboard se actualizará automáticamente allí.")
        except discord.Forbidden:
            error_msg = "❌ No tengo permisos para enviar mensajes en ese canal."
            if interaction.response.is_done(): await interaction.edit_original_response(content=error_msg)
            else: await interaction.followup.send(error_msg)
        except Exception as e:
            error_msg = f"❌ Ocurrió un error al enviar el mensaje: {e}"
            if interaction.response.is_done(): await interaction.edit_original_response(content=error_msg)
            else: await interaction.followup.send(error_msg)

    @app_commands.command(name="sync", description="Actualiza manualmente el Leaderboard del servidor.")
    @app_commands.default_permissions(manage_guild=True)
    async def sync_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        lb_data = await DBManager.get_guild_leaderboard(interaction.guild_id)
        if not lb_data:
            return await interaction.followup.send("❌ No hay ningún canal configurado. Usa `/linkcanal` primero.", ephemeral=True)
            
        channel_id, message_id = lb_data
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel or not hasattr(channel, 'fetch_message'):
            return await interaction.followup.send("❌ El canal configurado ya no existe o es inválido. Por favor configúralo de nuevo.", ephemeral=True)
            
        embed, file = await self.generate_leaderboard_data(interaction.guild)
        
        if not embed:
            embed = discord.Embed(
                title="🏆 TOP 10 Scrobbles",
                description="No hay suficientes usuarios vinculados aún. Usa `/link` para participar.",
                color=discord.Color.red()
            )
            file = None
            
        kwargs = {'embed': embed}
        if file:
            kwargs['attachments'] = [file]
        else:
            kwargs['attachments'] = []

        try:
            if message_id:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(**kwargs)
                    await interaction.followup.send(f"✅ Leaderboard sincronizado exitosamente en {channel.mention}.", ephemeral=True)
                except discord.NotFound:
                    kwargs.pop('attachments', None)
                    if file: kwargs['file'] = file
                    new_msg = await channel.send(**kwargs)
                    await DBManager.set_guild_leaderboard(interaction.guild_id, channel.id, new_msg.id)
                    await interaction.followup.send(f"✅ Se creó un nuevo mensaje de Leaderboard en {channel.mention}.", ephemeral=True)
            else:
                kwargs.pop('attachments', None)
                if file: kwargs['file'] = file
                new_msg = await channel.send(**kwargs)
                await DBManager.set_guild_leaderboard(interaction.guild_id, channel.id, new_msg.id)
                await interaction.followup.send(f"✅ Se creó un nuevo mensaje de Leaderboard en {channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"❌ No tengo permisos para enviar o editar mensajes en {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ocurrió un error al actualizar el leaderboard: {e}", ephemeral=True)

    async def generate_leaderboard_image(self, users_data: list[tuple[bytes, str]]) -> io.BytesIO:
        def generate():
            WIDTH, HEIGHT = 150, 150
            cols, rows = 5, 2
            
            canvas = Image.new('RGBA', (WIDTH * cols, HEIGHT * rows), color='#202225')
            
            try:
                font = ImageFont.truetype("arial.ttf", 14)
                emoji_font = ImageFont.truetype("arial.ttf", 26)
            except IOError:
                font = ImageFont.load_default()
                emoji_font = ImageFont.load_default()
                
            emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            with Pilmoji(canvas) as pilmoji:
                for idx, (img_bytes, name) in enumerate(users_data):
                    if idx >= 10: break
                    col = idx % cols
                    row = idx // cols
                    
                    x, y = col * WIDTH, row * HEIGHT
                    
                    try:
                        avatar = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
                        avatar = avatar.resize((WIDTH, HEIGHT))
                        canvas.paste(avatar, (x, y))
                    except Exception:
                        pass
                        
                    # Overlay
                    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(overlay)
                    rect_height = 30
                    draw.rectangle([0, HEIGHT - rect_height, WIDTH, HEIGHT], fill=(0, 0, 0, 180))
                    
                    # Text
                    display_name = name[:14] + '...' if len(name) > 14 else name
                    if hasattr(font, 'getbbox'):
                        bbox = font.getbbox(display_name)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                    else:
                        text_w, text_h = draw.textsize(display_name, font=font)
                    
                    text_x = (WIDTH - text_w) / 2
                    text_y = HEIGHT - rect_height + (rect_height - text_h) / 2 - 2
                    
                    draw.text((text_x, text_y), display_name, font=font, fill='white')
                    
                    # Combine
                    canvas.alpha_composite(overlay, dest=(x, y))
                    
                    # Añadir emoji arriba a la izquierda
                    pilmoji.text((x + 8, y + 8), emojis[idx], font=emoji_font)
                    
            buffer = io.BytesIO()
            canvas.convert('RGB').save(buffer, format='PNG')
            buffer.seek(0)
            return buffer
            
        return await asyncio.to_thread(generate)

    async def generate_leaderboard_data(self, guild: discord.Guild) -> tuple[discord.Embed, discord.File]:
        db_users = await DBManager.get_all_users()
        guild_member_ids = {m.id for m in guild.members}
        server_users = [u for u in db_users if u[0] in guild_member_ids]
        
        if not server_users:
            return None, None
            
        leaderboard_data = []
        
        for discord_id, lastfm_username in server_users:
            try:
                user_info = await self.client.get_user_info(lastfm_username)
                if user_info:
                    playcount = int(user_info.get('playcount', 0))
                    real_lastfm_name = user_info.get('name', lastfm_username)
                    member = guild.get_member(discord_id)
                    leaderboard_data.append((member, real_lastfm_name, playcount))
            except Exception:
                pass
                
        leaderboard_data.sort(key=lambda x: x[2], reverse=True)
        top_10 = leaderboard_data[:10]
        
        if not top_10:
            return None, None
            
        # Generar texto del embed
        embed = discord.Embed(
            title="🏆 TOP 10 Scrobbles",
            color=discord.Color.red()
        )
        
        description = ""
        avatars_to_download = []
        
        async with aiohttp.ClientSession() as session:
            for i, (member, lastfm_name, playcount) in enumerate(top_10, 1):
                # Formato: 1. @Usuario (lastfm_name linkeado) - 30.000
                formatted_playcount = f"{playcount:,}".replace(",", ".")
                description += f"**{i}.** {member.mention} ([{lastfm_name}](https://www.last.fm/user/{lastfm_name})) - {formatted_playcount}\n"
                
                # Descargar avatar
                avatar_url = member.display_avatar.url
                try:
                    async with session.get(avatar_url) as resp:
                        if resp.status == 200:
                            img_bytes = await resp.read()
                            avatars_to_download.append((img_bytes, member.display_name))
                        else:
                            # Avatar dummy si falla
                            avatars_to_download.append((b'', member.display_name))
                except Exception:
                    avatars_to_download.append((b'', member.display_name))
                    
        embed.description = description
        
        # Añadir footer con fecha
        now = datetime.now()
        embed.set_footer(text=f"Ultima Actualizacion • {now.strftime('%m/%d/%Y, %I:%M:%S %p')}")
        
        # Generar y adjuntar imagen
        image_buffer = await self.generate_leaderboard_image(avatars_to_download)
        file = discord.File(fp=image_buffer, filename="leaderboard.png")
        embed.set_image(url="attachment://leaderboard.png")
        
        return embed, file

    # Actualización automática cada 1 hora
    @tasks.loop(hours=1)
    async def leaderboard_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            lb_data = await DBManager.get_guild_leaderboard(guild.id)
            if lb_data:
                channel_id, message_id = lb_data
                channel = guild.get_channel(channel_id)
                if channel and hasattr(channel, 'fetch_message'):
                    embed, file = await self.generate_leaderboard_data(guild)
                    
                    if not embed:
                        embed = discord.Embed(
                            title="🏆 TOP 10 Scrobbles",
                            description="No hay suficientes usuarios vinculados aún. Usa `/link` para participar.",
                            color=discord.Color.red()
                        )
                        file = None
                        
                    kwargs = {'embed': embed}
                    if file:
                        kwargs['attachments'] = [file] # Al editar mensajes, se usa attachments en lugar de file
                    else:
                        kwargs['attachments'] = []

                    try:
                        if message_id:
                            try:
                                msg = await channel.fetch_message(message_id)
                                await msg.edit(**kwargs)
                            except discord.NotFound:
                                kwargs.pop('attachments', None)
                                if file: kwargs['file'] = file
                                new_msg = await channel.send(**kwargs)
                                await DBManager.set_guild_leaderboard(guild.id, channel.id, new_msg.id)
                        else:
                            kwargs.pop('attachments', None)
                            if file: kwargs['file'] = file
                            new_msg = await channel.send(**kwargs)
                            await DBManager.set_guild_leaderboard(guild.id, channel.id, new_msg.id)
                    except discord.Forbidden:
                        pass
                    except Exception as e:
                        print(f"Error actualizando leaderboard en {guild.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
