import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="디모 봇 도움말")
    async def help(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📚 디모 도움말",
            description="사용 가능한 명령어 목록",
            color=0x6aa9ff
        )

        embed.add_field(
            name="🎲 랜덤",
            value="/랜덤추첨\n/역할랜덤추첨",
            inline=False
        )

        embed.add_field(
            name="🍀 럭키",
            value="/오늘의운세\n/오늘의메뉴",
            inline=False
        )

        embed.add_field(
            name="✌ 게임",
            value="/가위바위보\n/전적\n/랭킹",
            inline=False
        )

        embed.add_field(
            name="⏰ 타이머",
            value="/타이머\n/타이머취소",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))