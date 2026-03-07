import discord
from discord.ext import commands
from discord import app_commands
import random

class RandomPick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="랜덤추첨", description="서버 인원 중 랜덤 추첨")
    async def random_pick(self, interaction: discord.Interaction, 봇제외: bool=True):

        members = interaction.guild.members

        if 봇제외:
            members = [m for m in members if not m.bot]

        if not members:
            return await interaction.response.send_message("추첨 인원이 없습니다")

        winner = random.choice(members)

        embed = discord.Embed(
            title="🎉 랜덤 추첨",
            description=f"당첨자: {winner.mention}",
            color=0x00fff8
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="역할랜덤추첨", description="특정 역할 랜덤")
    async def role_random(self, interaction: discord.Interaction, 역할: discord.Role):

        members = [m for m in 역할.members if not m.bot]

        if not members:
            return await interaction.response.send_message("인원이 없습니다")

        winner = random.choice(members)

        embed = discord.Embed(
            title="🎯 역할 랜덤",
            description=f"{역할.mention}\n\n🏆 {winner.mention}",
            color=0xff66cc
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RandomPick(bot))