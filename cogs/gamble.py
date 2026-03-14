import asyncio
import json
import os
import random
import tempfile
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

DATA_FILE = Path("data/economy.json")

MIN_BET = 10
MAX_BET = 100000
COOLDOWN = 5
BASE_PROBABILITY = 0.5
NORMAL_DELAY = 0.35
FINAL_DELAY = 0.85


def load_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        data = {"users": {}}
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {"users": {}}

        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        return data
    except Exception:
        data = {"users": {}}
        save_data(data)
        return data


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=str(DATA_FILE.parent), suffix=".tmp")

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=4)

        os.replace(temp_path, DATA_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def ensure_user(data, user_id):
    user_id = str(user_id)

    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}

    users = data["users"]

    if user_id not in users or not isinstance(users[user_id], dict):
        users[user_id] = {}

    user = users[user_id]

    defaults = {
        "money": 0,
        "last_attendance": "",
        "streak": 0,
        "total_attendance": 0,
        "win": 0,
        "lose": 0,
        "slot_win": 0,
        "slot_lose": 0,
        "inventory": [],
        "active_effects": {},
    }

    for k, v in defaults.items():
        if k not in user:
            if isinstance(v, list):
                user[k] = []
            elif isinstance(v, dict):
                user[k] = {}
            else:
                user[k] = v

    int_fields = ["money", "streak", "total_attendance", "win", "lose", "slot_win", "slot_lose"]
    for field in int_fields:
        try:
            user[field] = int(user.get(field, 0))
        except (TypeError, ValueError):
            user[field] = 0

        if user[field] < 0:
            user[field] = 0

    if not isinstance(user["inventory"], list):
        user["inventory"] = []

    if not isinstance(user["active_effects"], dict):
        user["active_effects"] = {}

    return user


class Gamble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def interaction_check(self, interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return False

        if interaction.user.bot:
            await interaction.response.send_message(
                "❌ 봇은 사용할 수 없어요.",
                ephemeral=True
            )
            return False

        return True

    def build_result_embed(self, user, before, after, win, all_in=False):
        mode = "올인" if all_in else "도박"

        if win:
            embed = discord.Embed(
                title="🎉 승리",
                description=f"```fix\n{before:,} → {after:,}\n```",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="😢 패배",
                description=f"```fix\n{before:,} → {after:,}\n```",
                color=discord.Color.red()
            )

        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url
        )
        embed.set_footer(text=f"Dimo Casino 🎰 · {mode}")
        return embed

    async def roll_animation(self, interaction, name, mode, probability):
        revealed = []
        success_count = 0

        for i in range(9):
            face = "●" if random.random() < probability else "○"

            if face == "●":
                success_count += 1

            revealed.append(face)
            frame = "✦ " + " ".join(revealed + ["·"] * (9 - len(revealed))) + " ✦"

            embed = discord.Embed(
                title=f"🪙 {name}님의 코인 토스",
                description=frame,
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"Dimo Casino 🎰 · {mode}")

            try:
                await interaction.edit_original_response(embed=embed)
            except discord.HTTPException:
                break

            if i == 7:
                heads = revealed.count("●")
                tails = revealed.count("○")

                if heads == 4 and tails == 4:
                    await asyncio.sleep(FINAL_DELAY)
                else:
                    await asyncio.sleep(NORMAL_DELAY)
            elif i < 8:
                await asyncio.sleep(NORMAL_DELAY)

        win = success_count >= 5
        return win

    async def process_gamble(self, interaction, amount, all_in=False):
        data = load_data()
        user = ensure_user(data, interaction.user.id)

        if amount < MIN_BET:
            await interaction.response.send_message(
                f"❌ 최소 베팅은 {MIN_BET:,} 코인이에요.",
                ephemeral=True
            )
            return

        if amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ 최대 베팅은 {MAX_BET:,} 코인이에요.",
                ephemeral=True
            )
            return

        if user["money"] < amount:
            await interaction.response.send_message(
                f"❌ 코인이 부족해요.\n현재: {user['money']:,}",
                ephemeral=True
            )
            return

        before = user["money"]
        name = interaction.user.display_name
        mode = "올인" if all_in else "도박"

        luck_bonus = 0
        if isinstance(user.get("active_effects"), dict):
            luck_bonus = user["active_effects"].get("luck", 0)

        try:
            luck_bonus = float(luck_bonus)
        except (TypeError, ValueError):
            luck_bonus = 0

        probability = min(max(BASE_PROBABILITY + luck_bonus, 0.0), 1.0)

        start_embed = discord.Embed(
            title=f"🪙 {name}님의 코인 토스",
            description="✦ · · · · · · · · · ✦",
            color=discord.Color.blurple()
        )

        if luck_bonus > 0:
            percent = int(luck_bonus * 100)
            start_embed.add_field(
                name="✨ 적용 효과",
                value=f"확률 증가 +{percent}%",
                inline=False
            )

        start_embed.set_footer(text=f"Dimo Casino 🎰 · {mode}")

        await interaction.response.send_message(embed=start_embed)

        win = await self.roll_animation(interaction, name, mode, probability)

        if win:
            user["money"] += amount
        else:
            user["money"] -= amount

        if user["money"] < 0:
            user["money"] = 0

        if isinstance(user.get("active_effects"), dict):
            user["active_effects"].pop("luck", None)

        save_data(data)

        result = self.build_result_embed(
            interaction.user,
            before,
            user["money"],
            win,
            all_in
        )

        try:
            await interaction.edit_original_response(embed=result)
        except discord.HTTPException:
            if interaction.response.is_done():
                await interaction.followup.send(embed=result)

    @app_commands.command(name="도박", description="코인을 걸고 승부해요.")
    @app_commands.describe(금액="베팅 금액")
    @app_commands.checks.cooldown(1, COOLDOWN)
    async def gamble(self, interaction, 금액: int):
        await self.process_gamble(interaction, 금액, all_in=False)

    @app_commands.command(name="올인", description="코인을 전부 걸어요.")
    @app_commands.checks.cooldown(1, COOLDOWN)
    async def all_in(self, interaction):
        data = load_data()
        user = ensure_user(data, interaction.user.id)

        if user["money"] < MIN_BET:
            await interaction.response.send_message(
                "❌ 올인을 하려면 최소 코인이 필요해요.",
                ephemeral=True
            )
            return

        amount = min(user["money"], MAX_BET)
        await self.process_gamble(interaction, amount, all_in=True)

    async def handle_error(self, interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"⏳ 잠시 후 다시 시도해주세요. ({error.retry_after:.1f}초)"
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
            return

        if isinstance(error, app_commands.CheckFailure):
            return

        message = "❌ 도박을 처리하는 중 문제가 생겼어요."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @gamble.error
    async def gamble_error(self, interaction, error):
        await self.handle_error(interaction, error)

    @all_in.error
    async def all_in_error(self, interaction, error):
        await self.handle_error(interaction, error)


async def setup(bot):
    await bot.add_cog(Gamble(bot))