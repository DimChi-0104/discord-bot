import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

print("=== gamble.py import 성공 ===")

DATA_FILE = "data/economy.json"
MIN_BET = 10
MAX_BET = 100000


def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        return data

    except (json.JSONDecodeError, OSError):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)
        return {"users": {}}


def save_data(data):
    os.makedirs("data", exist_ok=True)

    if not isinstance(data, dict):
        data = {"users": {}}

    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_user_data(data, user_id: int):
    user_id = str(user_id)

    if user_id not in data["users"] or not isinstance(data["users"][user_id], dict):
        data["users"][user_id] = {}

    user = data["users"][user_id]

    defaults = {
        "money": 0,
        "last_attendance": "",
        "streak": 0,
        "total_attendance": 0,
        "win": 0,
        "lose": 0
    }

    for key, value in defaults.items():
        if key not in user or not isinstance(user[key], type(value)):
            user[key] = value

    if user["money"] < 0:
        user["money"] = 0

    if user["streak"] < 0:
        user["streak"] = 0

    if user["total_attendance"] < 0:
        user["total_attendance"] = 0

    if user["win"] < 0:
        user["win"] = 0

    if user["lose"] < 0:
        user["lose"] = 0

    return user


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도박", description="재화를 걸고 도박합니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def gamble(self, interaction: discord.Interaction, 금액: int):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇 계정은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 < MIN_BET:
            await interaction.response.send_message(
                f"배팅 금액은 최소 `{MIN_BET}`코인 이상이어야 해요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_BET:
            await interaction.response.send_message(
                f"배팅 금액은 최대 `{MAX_BET}`코인까지 가능해요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        if user["money"] < 금액:
            await interaction.response.send_message(
                f"보유 재화가 부족해요.\n현재 보유 재화: `{user['money']} 코인`",
                ephemeral=True
            )
            return

        roll = random.randint(1, 100)

        if roll <= 5:
            reward = 금액 * 5
            user["money"] += reward
            user["win"] += 1
            result = f"대박! `5배` 당첨!\n`+{reward} 코인`"
            color = discord.Color.gold()

        elif roll <= 25:
            reward = 금액 * 2
            user["money"] += reward
            user["win"] += 1
            result = f"승리! `2배` 당첨!\n`+{reward} 코인`"
            color = discord.Color.green()

        elif roll <= 50:
            result = "본전입니다.\n변동 없음"
            color = discord.Color.blurple()

        else:
            user["money"] -= 금액
            user["lose"] += 1
            result = f"패배...\n`-{금액} 코인`"
            color = discord.Color.red()

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="도박 결과",
            description=(
                f"배팅 금액: `{금액} 코인`\n"
                f"주사위: `{roll}`\n\n"
                f"{result}\n\n"
                f"현재 보유 재화: `{user['money']} 코인`"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="올인", description="현재 보유한 모든 재화로 도박합니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def all_in(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇 계정은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        amount = user["money"]

        if amount < MIN_BET:
            await interaction.response.send_message(
                f"올인은 보유 재화가 최소 `{MIN_BET}`코인 이상일 때만 가능해요.\n"
                f"현재 보유 재화: `{amount} 코인`",
                ephemeral=True
            )
            return

        if amount > MAX_BET:
            await interaction.response.send_message(
                f"올인은 최대 `{MAX_BET}`코인까지만 가능해요.\n"
                f"현재 보유 재화: `{amount} 코인`\n"
                f"`/도박 금액:{MAX_BET}`처럼 직접 입력해서 사용해주세요.",
                ephemeral=True
            )
            return

        roll = random.randint(1, 100)

        if roll <= 5:
            reward = amount * 5
            user["money"] += reward
            user["win"] += 1
            result = f"대박! `5배` 당첨!\n`+{reward} 코인`"
            color = discord.Color.gold()

        elif roll <= 25:
            reward = amount * 2
            user["money"] += reward
            user["win"] += 1
            result = f"승리! `2배` 당첨!\n`+{reward} 코인`"
            color = discord.Color.green()

        elif roll <= 50:
            result = "본전입니다.\n변동 없음"
            color = discord.Color.blurple()

        else:
            user["money"] = 0
            user["lose"] += 1
            result = f"전부 잃었습니다...\n`-{amount} 코인`"
            color = discord.Color.red()

        save_data(data)

        embed = discord.Embed(
            title="올인 결과",
            description=(
                f"올인 금액: `{amount} 코인`\n"
                f"주사위: `{roll}`\n\n"
                f"{result}\n\n"
                f"현재 보유 재화: `{user['money']} 코인`"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    print("=== gamble.py setup 호출됨 ===")
    await bot.add_cog(Gamble(bot))