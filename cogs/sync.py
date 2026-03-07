import discord
from discord import app_commands
from discord.ext import commands

print("=== sync.py import 성공 ===")


class Sync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="동기화", description="슬래시 명령어를 전역 동기화합니다. (관리자 전용)")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        synced = await self.bot.tree.sync()
        await interaction.response.send_message(
            f"전역 동기화 완료: `{len(synced)}`개",
            ephemeral=True
        )

    @app_commands.command(name="길드동기화", description="현재 서버에 슬래시 명령어를 동기화합니다. (관리자 전용)")
    @app_commands.checks.has_permissions(administrator=True)
    async def guild_sync(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        self.bot.tree.copy_global_to(guild=guild)
        synced = await self.bot.tree.sync(guild=guild)

        await interaction.response.send_message(
            f"`{guild.name}` 길드 동기화 완료: `{len(synced)}`개",
            ephemeral=True
        )


async def setup(bot):
    print("=== sync.py setup 호출됨 ===")
    await bot.add_cog(Sync(bot))