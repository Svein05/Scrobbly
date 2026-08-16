import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Muestra la lista de comandos disponibles.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Ayuda de Last.fm Bot",
            description="Aquí tienes la lista de comandos disponibles para interactuar con tu música:",
            color=discord.Color.red() # Color temático de Last.fm
        )
        
        embed.add_field(
            name="`/link <username>`",
            value="Vincula tu cuenta de Discord con tu usuario de Last.fm.",
            inline=False
        )
        embed.add_field(
            name="`/np [usuario]`",
            value="Muestra la canción que estás escuchando actualmente (o la última). Puedes mencionar a otro usuario para ver la suya.",
            inline=False
        )
        embed.add_field(
            name="`/linkcanal <canal>`",
            value="*(Solo Admins)* Configura el canal de este servidor donde se publicarán los Leaderboards semanales de reproducciones.",
            inline=False
        )
        
        embed.set_footer(text="Integración con Last.fm")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
