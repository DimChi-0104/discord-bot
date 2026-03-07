import discord
from discord import app_commands
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="로드", description="새 Cog를 로드합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def load_cog(self, interaction: discord.Interaction, 이름: str):
        ext = f"cogs.{이름}"

        try:
            await self.bot.load_extension(ext)
            await interaction.response.send_message(
                f"✅ 로드 완료: `{ext}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 로드 실패: `{ext}`\n```{e}```",
                ephemeral=True
            )

    @app_commands.command(name="언로드", description="Cog를 언로드합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def unload_cog(self, interaction: discord.Interaction, 이름: str):
        ext = f"cogs.{이름}"

        try:
            await self.bot.unload_extension(ext)
            await interaction.response.send_message(
                f"✅ 언로드 완료: `{ext}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 언로드 실패: `{ext}`\n```{e}```",
                ephemeral=True
            )

    @app_commands.command(name="리로드", description="Cog를 다시 불러옵니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_cog(self, interaction: discord.Interaction, 이름: str):
        ext = f"cogs.{이름}"

        try:
            await self.bot.reload_extension(ext)
            await interaction.response.send_message(
                f"✅ 리로드 완료: `{ext}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 리로드 실패: `{ext}`\n```{e}```",
                ephemeral=True
            )

    @app_commands.command(name="동기화", description="슬래시 명령어를 동기화합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        try:
            synced = await self.bot.tree.sync()
            await interaction.response.send_message(
                f"✅ 전역 슬래시 명령어 동기화 완료 ({len(synced)}개)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 동기화 실패\n```{e}```",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))