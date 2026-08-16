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
    @app_commands.describe(canal="Canal de texto")
    @app_commands.default_permissions(manage_guild=True)
    async def link_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await DBManager.set_guild_leaderboard_channel(interaction.guild_id, canal.id)
        await interaction.response.send_message(f"✅ El canal {canal.mention} ha sido configurado para los Leaderboards.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Muestra el Top 10 de Scrobbles del servidor.")
    async def show_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        embed = await self.generate_leaderboard_embed(interaction.guild)
        if embed:
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ No hay suficientes usuarios vinculados o hubo un error al generar el Leaderboard.")

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

    # Tarea programada que se ejecuta cada 7 días (por ejemplo)
    @tasks.loop(hours=168)
    async def leaderboard_task(self):
        # Esperar a que el bot esté listo
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            channel_id = await DBManager.get_guild_leaderboard_channel(guild.id)
            if channel_id:
                channel = guild.get_channel(channel_id)
                if channel:
                    embed = await self.generate_leaderboard_embed(guild)
                    if embed:
                        await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
