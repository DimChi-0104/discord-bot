import json
import os
import random
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

DATA_FILE = "data/economy.json"
MIN_BET = 10
MAX_BET = 100000

NORMAL_SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "💎"]
HARD_SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "💎", "💀"]


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

    def _validate_basic(self, interaction: discord.Interaction, 금액: int | None = None):
        if interaction.guild is None:
            return "이 명령어는 서버에서만 사용할 수 있어요."

        if interaction.user.bot:
            return "봇 계정은 사용할 수 없어요."

        if 금액 is not None:
            if 금액 < MIN_BET:
                return f"배팅 금액은 최소 `{MIN_BET}`코인 이상이어야 해요."
            if 금액 > MAX_BET:
                return f"배팅 금액은 최대 `{MAX_BET}`코인까지 가능해요."

        return None

    async def _slot_animation(
        self,
        interaction: discord.Interaction,
        *,
        title: str,
        amount: int,
        final_rolls: list[str],
        result_text: str,
        current_money: int,
        color: discord.Color,
        footer_text: str,
        is_hard: bool = False
    ):
        symbol_pool = HARD_SLOT_SYMBOLS if is_hard else NORMAL_SLOT_SYMBOLS
        reel_count = 5 if is_hard else 3
        hidden = ["❔"] * reel_count

        start_embed = discord.Embed(
            title=title,
            description=(
                f"배팅 금액: `{amount:,} 코인`\n\n"
                f"`{' '.join(hidden)}`\n\n"
                f"🎲 슬롯을 돌리는 중..."
            ),
            color=discord.Color.blurple()
        )
        start_embed.set_footer(text=footer_text)
        await interaction.response.send_message(embed=start_embed)

        # 1차 연출
        await asyncio.sleep(0.4)
        frame1 = [random.choice(symbol_pool) for _ in range(reel_count)]
        embed1 = discord.Embed(
            title=title,
            description=(
                f"배팅 금액: `{amount:,} 코인`\n\n"
                f"`{' '.join(frame1)}`\n\n"
                f"🎰 릴이 돌아가는 중..."
            ),
            color=discord.Color.blurple()
        )
        embed1.set_footer(text=footer_text)
        await interaction.edit_original_response(embed=embed1)

        # 2차 연출
        await asyncio.sleep(0.5)
        frame2 = [random.choice(symbol_pool) for _ in range(reel_count)]
        embed2 = discord.Embed(
            title=title,
            description=(
                f"배팅 금액: `{amount:,} 코인`\n\n"
                f"`{' '.join(frame2)}`\n\n"
                f"✨ 결과를 확인하는 중..."
            ),
            color=discord.Color.blurple()
        )
        embed2.set_footer(text=footer_text)
        await interaction.edit_original_response(embed=embed2)

        # 마지막 긴장감
        await asyncio.sleep(0.7)

        final_embed = discord.Embed(
            title=title,
            description=(
                f"배팅 금액: `{amount:,} 코인`\n\n"
                f"`{' '.join(final_rolls)}`"
            ),
            color=color
        )
        final_embed.add_field(name="결과", value=result_text, inline=False)
        final_embed.add_field(name="현재 보유 재화", value=f"`{current_money:,} 코인`", inline=False)
        final_embed.set_footer(text=footer_text)

        await interaction.edit_original_response(embed=final_embed)

    @app_commands.command(name="도박", description="재화를 걸고 도박합니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def gamble(self, interaction: discord.Interaction, 금액: int):
        error = self._validate_basic(interaction, 금액)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        if user["money"] < 금액:
            await interaction.response.send_message(
                f"보유 재화가 부족해요.\n현재 보유 재화: `{user['money']:,} 코인`",
                ephemeral=True
            )
            return

        roll = random.randint(1, 100)

        if roll <= 5:
            reward = 금액 * 5
            user["money"] += reward
            user["win"] += 1
            result = f"🔥 대박! `5배` 당첨!\n`+{reward:,} 코인`"
            color = discord.Color.gold()

        elif roll <= 30:
            reward = 금액 * 2
            user["money"] += reward
            user["win"] += 1
            result = f"✅ 승리! `2배` 당첨!\n`+{reward:,} 코인`"
            color = discord.Color.green()

        elif roll <= 50:
            result = "➖ 본전입니다.\n변동 없음"
            color = discord.Color.blurple()

        else:
            user["money"] -= 금액
            user["lose"] += 1
            result = f"💥 패배...\n`-{금액:,} 코인`"
            color = discord.Color.red()

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="🎲 도박 결과",
            description=(
                f"배팅 금액: `{금액:,} 코인`\n"
                f"주사위: `{roll}`\n\n"
                f"{result}"
            ),
            color=color
        )
        embed.add_field(name="현재 보유 재화", value=f"`{user['money']:,} 코인`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="올인", description="현재 보유한 모든 재화로 도박합니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def all_in(self, interaction: discord.Interaction):
        error = self._validate_basic(interaction)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        amount = user["money"]

        if amount < MIN_BET:
            await interaction.response.send_message(
                f"올인은 보유 재화가 최소 `{MIN_BET}`코인 이상일 때만 가능해요.\n"
                f"현재 보유 재화: `{amount:,} 코인`",
                ephemeral=True
            )
            return

        if amount > MAX_BET:
            await interaction.response.send_message(
                f"올인은 최대 `{MAX_BET}`코인까지만 가능해요.\n"
                f"현재 보유 재화: `{amount:,} 코인`\n"
                f"`/도박 금액:{MAX_BET}`처럼 직접 입력해서 사용해주세요.",
                ephemeral=True
            )
            return

        roll = random.randint(1, 100)

        if roll <= 5:
            reward = amount * 5
            user["money"] += reward
            user["win"] += 1
            result = f"🔥 대박! `5배` 당첨!\n`+{reward:,} 코인`"
            color = discord.Color.gold()

        elif roll <= 30:
            reward = amount * 2
            user["money"] += reward
            user["win"] += 1
            result = f"✅ 승리! `2배` 당첨!\n`+{reward:,} 코인`"
            color = discord.Color.green()

        elif roll <= 50:
            result = "➖ 본전입니다.\n변동 없음"
            color = discord.Color.blurple()

        else:
            user["money"] = 0
            user["lose"] += 1
            result = f"💀 전부 잃었습니다...\n`-{amount:,} 코인`"
            color = discord.Color.red()

        save_data(data)

        embed = discord.Embed(
            title="💣 올인 결과",
            description=(
                f"올인 금액: `{amount:,} 코인`\n"
                f"주사위: `{roll}`\n\n"
                f"{result}"
            ),
            color=color
        )
        embed.add_field(name="현재 보유 재화", value=f"`{user['money']:,} 코인`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="도박랭킹", description="도박 승수 랭킹을 확인합니다.")
    async def gamble_ranking(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        data = load_data()
        users = data.get("users", {})
        ranking = []

        for user_id, info in users.items():
            if not isinstance(info, dict):
                continue

            try:
                member = interaction.guild.get_member(int(user_id))
            except ValueError:
                continue

            if member is None or member.bot:
                continue

            win = info.get("win", 0)
            lose = info.get("lose", 0)

            if not isinstance(win, int) or win < 0:
                win = 0
            if not isinstance(lose, int) or lose < 0:
                lose = 0

            total = win + lose
            if total == 0:
                continue

            ranking.append((member, win, lose, total))

        ranking.sort(key=lambda x: (-x[1], x[2], -x[3], x[0].display_name.lower()))
        top_10 = ranking[:10]

        if not top_10:
            await interaction.response.send_message(
                "아직 도박 전적 데이터가 없어요.",
                ephemeral=True
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for idx, (member, win, lose, total) in enumerate(top_10, start=1):
            prefix = medals[idx - 1] if idx <= 3 else f"{idx}위"
            win_rate = (win / total) * 100 if total > 0 else 0
            lines.append(
                f"{prefix} {member.display_name} - `승 {win} / 패 {lose}` · `승률 {win_rate:.1f}%`"
            )

        embed = discord.Embed(
            title="🎰 도박 랭킹 TOP 10",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="슬롯", description="슬롯머신을 돌립니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def slot(self, interaction: discord.Interaction, 금액: int):
        error = self._validate_basic(interaction, 금액)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        if user["money"] < 금액:
            await interaction.response.send_message(
                f"보유 재화가 부족해요.\n현재 보유 재화: `{user['money']:,} 코인`",
                ephemeral=True
            )
            return

        rolls = [random.choice(NORMAL_SLOT_SYMBOLS) for _ in range(3)]
        counts = {symbol: rolls.count(symbol) for symbol in NORMAL_SLOT_SYMBOLS}

        if counts["💎"] == 3:
            reward = 금액 * 10
            user["money"] += reward
            user["win"] += 1
            result_text = f"💎💎💎 잭팟!\n`+{reward:,} 코인` (`10배`)"
            color = discord.Color.gold()

        elif counts["🔔"] == 3:
            reward = 금액 * 5
            user["money"] += reward
            user["win"] += 1
            result_text = f"🔔🔔🔔 대박!\n`+{reward:,} 코인` (`5배`)"
            color = discord.Color.green()

        elif counts["🍋"] == 3:
            reward = 금액 * 4
            user["money"] += reward
            user["win"] += 1
            result_text = f"🍋🍋🍋 당첨!\n`+{reward:,} 코인` (`4배`)"
            color = discord.Color.green()

        elif counts["🍒"] == 3:
            reward = 금액 * 3
            user["money"] += reward
            user["win"] += 1
            result_text = f"🍒🍒🍒 당첨!\n`+{reward:,} 코인` (`3배`)"
            color = discord.Color.green()

        else:
            user["money"] -= 금액
            user["lose"] += 1
            result_text = f"꽝!\n`-{금액:,} 코인`"
            color = discord.Color.red()

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        await self._slot_animation(
            interaction,
            title="🎰 슬롯머신 결과",
            amount=금액,
            final_rolls=rolls,
            result_text=result_text,
            current_money=user["money"],
            color=color,
            footer_text="기본 슬롯 · 3칸 슬롯",
            is_hard=False
        )

    @app_commands.command(name="하드모드슬롯", description="5개가 전부 같아야 당첨되는 하드모드 슬롯입니다.")
    @app_commands.checks.cooldown(1, 5.0)
    async def hard_slot(self, interaction: discord.Interaction, 금액: int):
        error = self._validate_basic(interaction, 금액)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        data = load_data()
        user = get_user_data(data, interaction.user.id)

        if user["money"] < 금액:
            await interaction.response.send_message(
                f"보유 재화가 부족해요.\n현재 보유 재화: `{user['money']:,} 코인`",
                ephemeral=True
            )
            return

        rolls = [random.choice(HARD_SLOT_SYMBOLS) for _ in range(5)]

        if len(set(rolls)) == 1:
            reward = 금액 * 100
            user["money"] += reward
            user["win"] += 1
            result_text = (
                f"🔥 하드모드 잭팟!\n"
                f"`+{reward:,} 코인` (`100배`)\n"
                f"5칸이 전부 일치했습니다!"
            )
            color = discord.Color.gold()
        else:
            user["money"] -= 금액
            user["lose"] += 1
            result_text = (
                f"💀 실패!\n"
                f"`-{금액:,} 코인`\n"
                f"하드모드는 5칸 전부 같아야 당첨이에요."
            )
            color = discord.Color.red()

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        await self._slot_animation(
            interaction,
            title="🎰 하드모드 슬롯 결과",
            amount=금액,
            final_rolls=rolls,
            result_text=result_text,
            current_money=user["money"],
            color=color,
            footer_text="하드모드 · 5칸 전부 일치 시 100배",
            is_hard=True
        )


async def setup(bot):
    await bot.add_cog(Gamble(bot))