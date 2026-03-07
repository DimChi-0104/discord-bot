import discord
from discord.ext import commands
from discord import app_commands

print("=== gamble.py import 성공 ===")


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도박테스트", description="도박 테스트")
    async def gamble_test(self, interaction: discord.Interaction):
        await interaction.response.send_message("gamble cog 정상 작동")


async def setup(bot):
    print("=== gamble.py setup 호출됨 ===")
    await bot.add_cog(Gamble(bot))