import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio

from services.db_manager import DBManager
from services.lastfm_client import LastFMClient

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
            await interaction.response.send_message("❌ Debes seleccionar un canal de texto válido donde el bot pueda enviar mensajes.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        embed = await self.generate_leaderboard_embed(interaction.guild)
        if not embed:
            embed = discord.Embed(
                title=f"🏆 Top 10 Scrobbles Totales - {interaction.guild.name}",
                description="No hay suficientes usuarios vinculados aún. Usa `/link` para participar.",
                color=discord.Color.red()
            )
            
        try:
            msg = await canal.send(embed=embed)
            await DBManager.set_guild_leaderboard(interaction.guild_id, canal.id, msg.id)
            await interaction.followup.send(f"✅ El canal {canal.mention} ha sido configurado. El Leaderboard se actualizará automáticamente allí.")
        except discord.Forbidden:
            await interaction.followup.send("❌ No tengo permisos para enviar mensajes en ese canal.")
        except Exception as e:
            await interaction.followup.send(f"❌ Ocurrió un error al enviar el mensaje: {e}")

    async def generate_leaderboard_embed(self, guild: discord.Guild) -> discord.Embed:
        db_users = await DBManager.get_all_users()
        
        # Filtrar solo miembros del servidor actual
        guild_members = guild.members
        guild_member_ids = {m.id for m in guild_members}
        
        server_users = [u for u in db_users if u[0] in guild_member_ids]
        
        if not server_users:
            return None
            
        leaderboard_data = []
        
        for discord_id, lastfm_username in server_users:
            try:
                user_info = await self.client.get_user_info(lastfm_username)
                if user_info:
                    playcount = int(user_info.get('playcount', 0))
                    member = guild.get_member(discord_id)
                    member_name = member.display_name if member else "Desconocido"
                    leaderboard_data.append((member_name, lastfm_username, playcount))
            except Exception:
                # Ignorar usuarios con error para no bloquear el leaderboard
                pass
                
        # Ordenar por playcount descendente y tomar Top 10
        leaderboard_data.sort(key=lambda x: x[2], reverse=True)
        top_10 = leaderboard_data[:10]
        
        if not top_10:
            return None
            
        embed = discord.Embed(
            title=f"🏆 Top 10 Scrobbles Totales - {guild.name}",
            color=discord.Color.red()
        )
        
        description = ""
        for i, (member_name, lastfm_name, playcount) in enumerate(top_10, 1):
            medalla = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            description += f"{medalla} **{member_name}** (`{lastfm_name}`) - **{playcount:,}** scrobbles\n"
            
        embed.description = description
        return embed

    # Tarea programada que se ejecuta cada 12 horas para mantenerlo actualizado
    @tasks.loop(hours=12)
    async def leaderboard_task(self):
        # Esperar a que el bot esté listo
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            lb_data = await DBManager.get_guild_leaderboard(guild.id)
            if lb_data:
                channel_id, message_id = lb_data
                channel = guild.get_channel(channel_id)
                if channel and hasattr(channel, 'fetch_message'):
                    embed = await self.generate_leaderboard_embed(guild)
                    if not embed:
                        embed = discord.Embed(
                            title=f"🏆 Top 10 Scrobbles Totales - {guild.name}",
                            description="No hay suficientes usuarios vinculados aún. Usa `/link` para participar.",
                            color=discord.Color.red()
                        )
                    try:
                        if message_id:
                            try:
                                msg = await channel.fetch_message(message_id)
                                await msg.edit(embed=embed)
                            except discord.NotFound:
                                # Si el mensaje fue borrado, enviamos uno nuevo
                                new_msg = await channel.send(embed=embed)
                                await DBManager.set_guild_leaderboard(guild.id, channel.id, new_msg.id)
                        else:
                            new_msg = await channel.send(embed=embed)
                            await DBManager.set_guild_leaderboard(guild.id, channel.id, new_msg.id)
                    except discord.Forbidden:
                        pass # No hay permisos
                    except Exception as e:
                        print(f"Error actualizando leaderboard en {guild.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
