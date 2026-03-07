import random

import discord
from discord import app_commands
from discord.ext import commands


class RandomPick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="랜덤추첨", description="서버 인원 중 랜덤으로 한 명을 뽑습니다.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(봇제외="봇 계정을 제외할까요?")
    async def random_pick(
        self,
        interaction: discord.Interaction,
        봇제외: bool = True
    ):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "❌ 서버에서만 사용할 수 있습니다.",
                ephemeral=True
            )

        members = interaction.guild.members

        if 봇제외:
            members = [m for m in members if not m.bot]

        if not members:
            return await interaction.response.send_message(
                "❌ 추첨할 인원이 없습니다.",
                ephemeral=True
            )

        winner = random.choice(members)

        embed = discord.Embed(
            title="🎉 랜덤 추첨 결과",
            description=f"당첨자: {winner.mention}",
            color=0x00FFF8
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        embed.set_footer(text=f"총 참여 인원: {len(members)}명")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="역할랜덤추첨", description="특정 역할 보유자 중 랜덤 추첨")
    @app_commands.checks.has_permissions(administrator=True)
    async def role_random_pick(
        self,
        interaction: discord.Interaction,
        역할: discord.Role
    ):
        members = [m for m in 역할.members if not m.bot]

        if not members:
            return await interaction.response.send_message(
                "❌ 해당 역할 인원이 없습니다.",
                ephemeral=True
            )

        winner = random.choice(members)

        embed = discord.Embed(
            title="🎯 역할 랜덤 추첨",
            description=f"역할: {역할.mention}\n\n🏆 당첨자: {winner.mention}",
            color=0xFF66CC
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        embed.set_footer(text=f"총 참여 인원: {len(members)}명")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RandomPick(bot))