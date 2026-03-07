import logging
import os
import traceback

import discord
from discord import app_commands
from discord.ext import commands

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/error.log",
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        original = getattr(error, "original", error)

        # 1. 관리자 권한 부족
        if isinstance(error, app_commands.MissingPermissions):
            message = "⚠ 관리자만 사용할 수 있는 명령어입니다."

        # 2. 쿨타임
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"⏳ 잠시 후 다시 시도해주세요. ({error.retry_after:.1f}초 남음)"

        # 3. DM 사용 불가 / 서버 전용 명령어
        elif isinstance(error, app_commands.NoPrivateMessage):
            message = "📌 이 명령어는 서버에서만 사용할 수 있습니다."

        # 4. 일반 권한 오류
        elif isinstance(error, app_commands.BotMissingPermissions):
            message = "⚠ 봇에게 필요한 권한이 부족합니다."

        # 5. 체크 실패
        elif isinstance(error, app_commands.CheckFailure):
            message = "⚠ 이 명령어를 사용할 수 없습니다."

        # 6. 잘못된 입력값
        elif isinstance(error, app_commands.CommandInvokeError):
            if isinstance(original, discord.Forbidden):
                message = "⚠ 권한이 부족하거나 접근할 수 없는 작업입니다."
            else:
                logging.error(traceback.format_exc())
                message = "⚠ 명령어 실행 중 오류가 발생했습니다."

        # 7. 그 외 알 수 없는 오류
        else:
            logging.error(traceback.format_exc())
            message = "⚠ 알 수 없는 오류가 발생했습니다."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))