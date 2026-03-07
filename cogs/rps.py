import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

RECORD_FILE = "data/rps_records.json"


def load_records():
    if not os.path.exists(RECORD_FILE):
        os.makedirs("data", exist_ok=True)
        with open(RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(RECORD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_records(data):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class RPS(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="가위바위보", description="봇과 가위바위보를 합니다")
    async def rps(self, interaction: discord.Interaction, 선택: str):

        choices = ["가위", "바위", "보"]

        if 선택 not in choices:
            return await interaction.response.send_message(
                "❌ 가위 / 바위 / 보 중 하나를 입력하세요."
            )

        bot_choice = random.choice(choices)

        result = ""

        if 선택 == bot_choice:
            result = "🤝 무승부!"
        elif (
            (선택 == "가위" and bot_choice == "보")
            or (선택 == "바위" and bot_choice == "가위")
            or (선택 == "보" and bot_choice == "바위")
        ):
            result = "🏆 당신의 승리!"
        else:
            result = "💀 당신의 패배!"

        data = load_records()

        uid = str(interaction.user.id)

        if uid not in data:
            data[uid] = {
                "name": interaction.user.display_name,
                "win": 0,
                "lose": 0,
                "draw": 0
            }

        if result.startswith("🏆"):
            data[uid]["win"] += 1
        elif result.startswith("💀"):
            data[uid]["lose"] += 1
        else:
            data[uid]["draw"] += 1

        save_records(data)

        embed = discord.Embed(
            title="✌ 가위바위보",
            description=(
                f"당신: **{선택}**\n"
                f"봇: **{bot_choice}**\n\n"
                f"{result}"
            ),
            color=0x00ffaa
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="전적", description="가위바위보 전적 확인")
    async def record(self, interaction: discord.Interaction, 유저: discord.Member | None = None):

        user = 유저 or interaction.user
        data = load_records()

        uid = str(user.id)

        if uid not in data:
            return await interaction.response.send_message("전적이 없습니다.")

        r = data[uid]

        embed = discord.Embed(
            title=f"📊 {r['name']}의 전적",
            description=(
                f"🏆 승: {r['win']}\n"
                f"💀 패: {r['lose']}\n"
                f"🤝 무: {r['draw']}"
            ),
            color=0x00ffaa
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="랭킹", description="가위바위보 승리 랭킹")
    async def ranking(self, interaction: discord.Interaction):

        data = load_records()

        if not data:
            return await interaction.response.send_message("랭킹 데이터가 없습니다.")

        ranked = sorted(data.values(), key=lambda x: x["win"], reverse=True)[:10]

        desc = ""

        for i, u in enumerate(ranked, 1):
            desc += f"**{i}위** {u['name']} 🏆 {u['win']}승\n"

        embed = discord.Embed(
            title="🏆 가위바위보 랭킹",
            description=desc,
            color=0xffcc00
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RPS(bot))