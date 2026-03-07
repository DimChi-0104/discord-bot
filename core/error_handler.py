import discord
from discord.ext import commands
import traceback
import logging

logging.basicConfig(
    filename="logs/error.log",
    level=logging.ERROR,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
)

class ErrorHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):

        logging.error(traceback.format_exc())

        await interaction.response.send_message(
            "⚠ 명령어 실행 중 오류가 발생했습니다.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))