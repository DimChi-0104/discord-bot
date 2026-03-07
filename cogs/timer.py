import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

CONFIG_FILE = "data/config.json"
TIMER_FILE = "data/timer_data.json"
KST = ZoneInfo("Asia/Seoul")


def load_json(path: str, default):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class Timer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_json(CONFIG_FILE, {"timer_channel": None})
        self.timers = load_json(TIMER_FILE, {})
        self.timer_loop.start()

    def cog_unload(self):
        self.timer_loop.cancel()

    @app_commands.command(name="타이머채널설정", description="타이머를 보낼 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_timer_channel(
        self,
        interaction: discord.Interaction,
        채널: discord.TextChannel
    ):
        self.config["timer_channel"] = 채널.id
        save_json(CONFIG_FILE, self.config)

        await interaction.response.send_message(
            f"✅ 타이머 채널이 {채널.mention} 으로 설정되었습니다.",
            ephemeral=True
        )

    @app_commands.command(name="타이머", description="KST 기준 시각 타이머를 생성합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def timer(
        self,
        interaction: discord.Interaction,
        시각: str,
        공지: str,
        멘션역할: discord.Role | None = None
    ):
        if not self.config.get("timer_channel"):
            return await interaction.response.send_message(
                "⚠ 타이머 채널이 설정되지 않았습니다. `/타이머채널설정`을 먼저 사용해주세요.",
                ephemeral=True
            )

        try:
            hour, minute = map(int, 시각.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "⏰ 시각 형식은 `18:30` 처럼 입력해주세요.",
                ephemeral=True
            )

        now = datetime.now(KST)
        end_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if end_time <= now:
            end_time += timedelta(days=1)

        channel = self.bot.get_channel(self.config["timer_channel"])
        if channel is None:
            return await interaction.response.send_message(
                "⚠ 설정된 타이머 채널을 찾을 수 없습니다.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="⏰ 타이머 시작",
            description=공지,
            color=0xFFCC00
        )
        embed.add_field(
            name="종료 시각 (KST)",
            value=end_time.strftime("%H:%M"),
            inline=False
        )
        embed.set_footer(text="남은 시간 계산 중...")

        msg = await channel.send(embed=embed)

        self.timers[str(msg.id)] = {
            "channel_id": channel.id,
            "end_time": end_time.isoformat(),
            "notice": 공지,
            "role_id": 멘션역할.id if 멘션역할 else None
        }
        save_json(TIMER_FILE, self.timers)

        await interaction.response.send_message(
            "✅ 타이머 생성 완료",
            ephemeral=True
        )

    @app_commands.command(name="타이머취소", description="생성된 타이머를 취소합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def timer_cancel(
        self,
        interaction: discord.Interaction,
        메시지아이디: str
    ):
        if 메시지아이디 not in self.timers:
            return await interaction.response.send_message(
                "❌ 해당 타이머를 찾을 수 없습니다.",
                ephemeral=True
            )

        data = self.timers.pop(메시지아이디)
        save_json(TIMER_FILE, self.timers)

        channel = self.bot.get_channel(data["channel_id"])
        if channel is not None:
            try:
                msg = await channel.fetch_message(int(메시지아이디))
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException:
                pass

        await interaction.response.send_message(
            "✅ 타이머 취소 완료",
            ephemeral=True
        )

    @tasks.loop(seconds=5)
    async def timer_loop(self):
        now = datetime.now(KST)
        remove = []

        for msg_id, data in list(self.timers.items()):
            end_time = datetime.fromisoformat(data["end_time"]).astimezone(KST)
            remaining = int((end_time - now).total_seconds())

            channel = self.bot.get_channel(data["channel_id"])
            if channel is None:
                remove.append(msg_id)
                continue

            try:
                msg = await channel.fetch_message(int(msg_id))
            except discord.NotFound:
                remove.append(msg_id)
                continue
            except discord.HTTPException:
                continue

            if remaining <= 0:
                end_embed = discord.Embed(
                    title="✅ 타이머 종료",
                    description=data["notice"],
                    color=0x00FF00
                )
                await msg.edit(embed=end_embed)

                if data.get("role_id"):
                    await channel.send(f"🔔 타이머 종료 알림 <@&{data['role_id']}>")

                remove.append(msg_id)
                continue

            total_blocks = 10
            filled = max(0, min(total_blocks, remaining // 60))
            bar_text = "🟩" * filled + "⬛" * (total_blocks - filled)

            embed = discord.Embed(
                title="⏰ 타이머 진행 중",
                description=f"{data['notice']}\n\n{bar_text}",
                color=0xFFCC00
            )
            embed.add_field(
                name="종료 시각 (KST)",
                value=end_time.strftime("%H:%M"),
                inline=False
            )
            embed.set_footer(
                text=f"남은 시간: {remaining // 60}분 {remaining % 60}초"
            )

            await msg.edit(embed=embed)

        for r in remove:
            self.timers.pop(r, None)

        save_json(TIMER_FILE, self.timers)

    @timer_loop.before_loop
    async def before_timer_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Timer(bot))