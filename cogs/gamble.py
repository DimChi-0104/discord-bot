import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

DATA_FILE = "data/economy.json"

MIN_BET = 10
MAX_BET = 100000

BASE_WIN_CHANCE = 0.45
LUCK_BONUS_CHANCE = 0.05  # 행운권 사용 시 45% -> 50%

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "💎", "💀"]
SLOT_REWARD_MULTIPLIER = 100


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

    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    os.replace(temp_file, DATA_FILE)


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
        "lose": 0,
        "slot_win": 0,
        "slot_lose": 0,
        "inventory": {},
        "active_effects": {
            "luck": 0,
            "title_ticket": 0,
            "nickname_change": 0
        }
    }

    for key, value in defaults.items():
        if key not in user or not isinstance(user[key], type(value)):
            user[key] = value

    if "inventory" not in user or not isinstance(user["inventory"], dict):
        user["inventory"] = {}

    if "active_effects" not in user or not isinstance(user["active_effects"], dict):
        user["active_effects"] = {}

    user["active_effects"].setdefault("luck", 0)
    user["active_effects"].setdefault("title_ticket", 0)
    user["active_effects"].setdefault("nickname_change", 0)

    if user["money"] < 0:
        user["money"] = 0
    if user["win"] < 0:
        user["win"] = 0
    if user["lose"] < 0:
        user["lose"] = 0
    if user["slot_win"] < 0:
        user["slot_win"] = 0
    if user["slot_lose"] < 0:
        user["slot_lose"] = 0
    if user["streak"] < 0:
        user["streak"] = 0
    if user["total_attendance"] < 0:
        user["total_attendance"] = 0

    return user


def roll_slot(luck_active: bool):
    """
    기본:
    - 5칸 전부 랜덤
    - 5개 전부 동일하면 당첨

    행운권 적용:
    - 특정 심볼로 약간 몰리게 해서 잭팟 확률만 소폭 상승
    - 경제 밸런스를 위해 과한 버프는 피함
    """
    if not luck_active:
        result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
        is_jackpot = len(set(result)) == 1
        return result, is_jackpot

    target_symbol = random.choice(SLOT_SYMBOLS)
    result = []

    for _ in range(5):
        # 안정 버전:
        # 20% 확률로 target_symbol 고정
        # 나머지 80%는 전체 랜덤
        # 최종적으로 target_symbol이 나올 확률이 약 36% 수준
        if random.random() < 0.20:
            result.append(target_symbol)
        else:
            result.append(random.choice(SLOT_SYMBOLS))

    is_jackpot = len(set(result)) == 1
    return result, is_jackpot


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
                f"최소 배팅 금액은 `{MIN_BET}`코인이에요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_BET:
            await interaction.response.send_message(
                f"최대 배팅 금액은 `{MAX_BET}`코인이에요.",
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

        active_effects = user.get("active_effects", {})
        luck_active = active_effects.get("luck", 0) > 0

        win_chance = BASE_WIN_CHANCE
        if luck_active:
            win_chance += LUCK_BONUS_CHANCE

        is_win = random.random() < win_chance

        if luck_active:
            active_effects["luck"] = 0

        if is_win:
            user["money"] += 금액
            user["win"] += 1
            result_text = "승리"
            reward_text = f"+{금액} 코인"
            color = discord.Color.green()
        else:
            user["money"] -= 금액
            user["lose"] += 1

            if user["money"] < 0:
                user["money"] = 0

            result_text = "패배"
            reward_text = f"-{금액} 코인"
            color = discord.Color.red()

        save_data(data)

        bonus_text = "🍀 행운권 발동! 승률 +5%" if luck_active else "없음"

        embed = discord.Embed(
            title=f"🎲 도박 {result_text}",
            description=(
                f"{interaction.user.mention}님이 `{금액} 코인`을 걸었어요.\n\n"
                f"결과: `{result_text}`\n"
                f"변동 재화: `{reward_text}`\n"
                f"적용 확률: `{int(win_chance * 100)}%`\n"
                f"행운 효과: `{bonus_text}`\n\n"
                f"현재 보유 재화: `{user['money']} 코인`\n"
                f"전적: `{user['win']}승 / {user['lose']}패`"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="올인", description="현재 보유한 재화를 모두 걸고 도박합니다.")
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

        money = user["money"]

        if money < MIN_BET:
            await interaction.response.send_message(
                f"올인을 하려면 최소 `{MIN_BET}`코인 이상 보유하고 있어야 해요.",
                ephemeral=True
            )
            return

        bet_amount = min(money, MAX_BET)

        active_effects = user.get("active_effects", {})
        luck_active = active_effects.get("luck", 0) > 0

        win_chance = BASE_WIN_CHANCE
        if luck_active:
            win_chance += LUCK_BONUS_CHANCE

        is_win = random.random() < win_chance

        if luck_active:
            active_effects["luck"] = 0

        if is_win:
            user["money"] += bet_amount
            user["win"] += 1
            result_text = "승리"
            reward_text = f"+{bet_amount} 코인"
            color = discord.Color.green()
        else:
            user["money"] -= bet_amount
            user["lose"] += 1

            if user["money"] < 0:
                user["money"] = 0

            result_text = "패배"
            reward_text = f"-{bet_amount} 코인"
            color = discord.Color.red()

        save_data(data)

        bonus_text = "🍀 행운권 발동! 승률 +5%" if luck_active else "없음"

        embed = discord.Embed(
            title=f"💥 올인 {result_text}",
            description=(
                f"{interaction.user.mention}님이 `{bet_amount} 코인`으로 올인했어요.\n\n"
                f"결과: `{result_text}`\n"
                f"변동 재화: `{reward_text}`\n"
                f"적용 확률: `{int(win_chance * 100)}%`\n"
                f"행운 효과: `{bonus_text}`\n\n"
                f"현재 보유 재화: `{user['money']} 코인`\n"
                f"전적: `{user['win']}승 / {user['lose']}패`"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="슬롯", description="하드모드 슬롯을 돌립니다. 5개 전부 같아야 100배 지급!")
    @app_commands.checks.cooldown(1, 5.0)
    async def slot(self, interaction: discord.Interaction, 금액: int):
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
                f"최소 배팅 금액은 `{MIN_BET}`코인이에요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_BET:
            await interaction.response.send_message(
                f"최대 배팅 금액은 `{MAX_BET}`코인이에요.",
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

        active_effects = user.get("active_effects", {})
        luck_active = active_effects.get("luck", 0) > 0

        result, is_jackpot = roll_slot(luck_active)

        if luck_active:
            active_effects["luck"] = 0

        slot_line = " │ ".join(result)

        if is_jackpot:
            reward = 금액 * SLOT_REWARD_MULTIPLIER
            user["money"] += reward
            user["slot_win"] += 1

            result_text = "🎉 JACKPOT 🎉"
            reward_text = f"+{reward} 코인"
            color = discord.Color.gold()
        else:
            user["money"] -= 금액
            user["slot_lose"] += 1

            if user["money"] < 0:
                user["money"] = 0

            result_text = "실패"
            reward_text = f"-{금액} 코인"
            color = discord.Color.red()

        save_data(data)

        bonus_text = "🍀 행운권 발동! 슬롯 확률 증가" if luck_active else "없음"
        slot_effect_text = "🍀 행운이 슬롯을 감쌉니다!\n\n" if luck_active else ""
        jackpot_text = "💰 100배 당첨!\n\n" if is_jackpot else ""

        embed = discord.Embed(
            title=f"🎰 슬롯 {result_text}",
            description=(
                f"{interaction.user.mention}님이 `{금액} 코인`을 걸고 슬롯을 돌렸어요.\n\n"
                f"{slot_effect_text}"
                f"`{slot_line}`\n\n"
                f"{jackpot_text}"
                f"결과: `{result_text}`\n"
                f"변동 재화: `{reward_text}`\n"
                f"행운 효과: `{bonus_text}`\n\n"
                f"현재 보유 재화: `{user['money']} 코인`\n"
                f"슬롯 전적: `{user['slot_win']}승 / {user['slot_lose']}패`\n"
                f"규칙: `5개 전부 동일 시 {SLOT_REWARD_MULTIPLIER}배 지급`"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="도박랭킹", description="도박 승수를 기준으로 랭킹을 확인합니다.")
    async def gamble_ranking(self, interaction: discord.Interaction):
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

            if not isinstance(win, int):
                win = 0
            if not isinstance(lose, int):
                lose = 0

            ranking.append((member, win, lose))

        ranking.sort(key=lambda x: x[1], reverse=True)
        top_10 = ranking[:10]

        if not top_10:
            await interaction.response.send_message(
                "아직 도박 데이터가 없어요.",
                ephemeral=True
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for idx, (member, win, lose) in enumerate(top_10, start=1):
            prefix = medals[idx - 1] if idx <= 3 else f"{idx}위"
            lines.append(f"{prefix} {member.display_name} - `{win}승 / {lose}패`")

        embed = discord.Embed(
            title="🎲 도박 랭킹 TOP 10",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Gamble(bot))