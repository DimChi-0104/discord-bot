import discord
from discord import app_commands
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="동기화", description="슬래시 명령어를 서버에 동기화합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):

        try:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)

            await interaction.response.send_message(
                f"✅ 슬래시 명령어 동기화 완료 ({len(synced)}개)",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ 동기화 실패\n```{e}```",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))