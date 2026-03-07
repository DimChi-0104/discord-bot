import discord
from discord import app_commands
from discord.ext import commands


class DimoHelp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="디모 봇 도움말을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📚 디모 도움말",
            description="디모는 서버 관리를 도와주고 일부 편의 기능도 제공하는 디스코드 봇입니다.",
            color=0x6AA9FF
        )

        embed.add_field(
            name="🛠 서버 관리 기능",
            value=(
                "`/랜덤추첨`\n"
                "`/역할랜덤추첨`\n"
                "`/타이머채널설정`\n"
                "`/타이머`\n"
                "`/타이머취소`\n"
                "`/동기화`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 부가 기능",
            value=(
                "`/오늘의운세`\n"
                "`/오늘의메뉴`\n"
                "`/가위바위보`\n"
                "`/전적`\n"
                "`/랭킹`"
            ),
            inline=False
        )

        embed.set_footer(text="Dimo | Server Support Bot")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DimoHelp(bot))