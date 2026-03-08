import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta, timezone

DATA_FILE = "data/economy.json"

KST = timezone(timedelta(hours=9))
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

RENT_COOLDOWN = timedelta(minutes=30)
MAX_RENT_TIME = timedelta(hours=24)
RENT_TAX_RATE = 0.05

PROPERTIES = {
    "원룸": {
        "price": 50000,
        "income": 200
    },
    "상가": {
        "price": 200000,
        "income": 900
    },
    "빌딩": {
        "price": 1000000,
        "income": 6000
    }
}

PROPERTY_LIMITS = {
    "원룸": None,
    "상가": 5,
    "빌딩": 1
}


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


def parse_datetime(value: str):
    if not value or not isinstance(value, str):
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=KST)
        except ValueError:
            continue

    return None


def get_user(data, user_id: int):
    user_id = str(user_id)

    if user_id not in data["users"] or not isinstance(data["users"][user_id], dict):
        data["users"][user_id] = {}

    user = data["users"][user_id]

    defaults = {
        "money": 0,
        "properties": {
            "원룸": 0,
            "상가": 0,
            "빌딩": 0
        },
        "last_rent": ""
    }

    for key, value in defaults.items():
        if key not in user or not isinstance(user[key], type(value)):
            user[key] = value

    if "properties" not in user or not isinstance(user["properties"], dict):
        user["properties"] = {
            "원룸": 0,
            "상가": 0,
            "빌딩": 0
        }

    user["properties"].setdefault("원룸", 0)
    user["properties"].setdefault("상가", 0)
    user["properties"].setdefault("빌딩", 0)

    if not isinstance(user["money"], int) or user["money"] < 0:
        user["money"] = 0

    return user


class RealEstate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="부동산", description="구매 가능한 부동산 목록을 확인합니다.")
    async def estate(self, interaction: discord.Interaction):
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

        embed = discord.Embed(
            title="🏢 디모 부동산",
            description="구매 가능한 부동산 목록입니다.",
            color=discord.Color.green()
        )

        for name, info in PROPERTIES.items():
            limit = PROPERTY_LIMITS.get(name)

            if limit is None:
                limit_text = "무제한"
            else:
                limit_text = f"최대 {limit}개"

            embed.add_field(
                name=name,
                value=(
                    f"가격: `{info['price']:,} 코인`\n"
                    f"수익: `{info['income']:,} 코인 / 30분`\n"
                    f"구매 제한: `{limit_text}`"
                ),
                inline=False
            )

        embed.set_footer(text="임대료는 30분마다 누적되며 최대 24시간까지만 쌓여요. 수령 시 세금 5%가 적용돼요.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="부동산구매", description="부동산을 구매합니다.")
    async def buy_estate(self, interaction: discord.Interaction, 이름: str):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        if 이름 not in PROPERTIES:
            await interaction.response.send_message(
                "존재하지 않는 부동산이에요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user(data, interaction.user.id)

        current_count = user["properties"].get(이름, 0)
        limit = PROPERTY_LIMITS.get(이름)

        if limit is not None and current_count >= limit:
            await interaction.response.send_message(
                f"{이름}은(는) 최대 `{limit}개`까지 구매할 수 있어요.",
                ephemeral=True
            )
            return

        price = PROPERTIES[이름]["price"]

        if user["money"] < price:
            await interaction.response.send_message(
                f"재화가 부족해요.\n필요 재화: `{price:,} 코인`\n현재 재화: `{user['money']:,} 코인`",
                ephemeral=True
            )
            return

        user["money"] -= price
        user["properties"][이름] = current_count + 1

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="🏢 부동산 구매 완료",
            description=(
                f"{interaction.user.mention}님이 **{이름}**을(를) 구매했어요.\n\n"
                f"보유 수량: `{user['properties'][이름]}개`\n"
                f"남은 재화: `{user['money']:,} 코인`"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="부동산목록", description="보유 중인 부동산을 확인합니다.")
    async def estate_list(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user(data, interaction.user.id)

        lines = []
        total_income_per_cycle = 0

        for name, info in PROPERTIES.items():
            count = user["properties"].get(name, 0)
            income = info["income"] * count
            total_income_per_cycle += income
            lines.append(f"{name}: `{count}개` (30분당 `{income:,} 코인`)")

        embed = discord.Embed(
            title="🏠 내 부동산",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="예상 수익",
            value=f"총 30분당 `{total_income_per_cycle:,} 코인`",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="임대료", description="쌓인 임대료를 수령합니다.")
    async def rent(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if interaction.user.bot:
            await interaction.response.send_message(
                "봇은 사용할 수 없어요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user(data, interaction.user.id)

        now = datetime.now(KST)
        last = parse_datetime(user["last_rent"])

        if last is not None:
            diff = now - last

            if diff > MAX_RENT_TIME:
                diff = MAX_RENT_TIME

            cycles = diff // RENT_COOLDOWN
        else:
            cycles = 1

        if cycles <= 0:
            next_time = last + RENT_COOLDOWN
            remain = next_time - now
            total_seconds = max(0, int(remain.total_seconds()))
            minutes, seconds = divmod(total_seconds, 60)

            await interaction.response.send_message(
                f"아직 임대료를 받을 수 없어요.\n남은 시간: `{minutes}분 {seconds}초`",
                ephemeral=True
            )
            return

        owned_any = False
        detail_lines = []
        total_income = 0

        for name, info in PROPERTIES.items():
            count = user["properties"].get(name, 0)

            if count > 0:
                owned_any = True
                income = info["income"] * count * cycles
                total_income += income
                detail_lines.append(
                    f"{name}: `{count}개` × `{cycles}회` = `{income:,} 코인`"
                )

        if not owned_any:
            await interaction.response.send_message(
                "보유한 부동산이 없어요.",
                ephemeral=True
            )
            return

        tax = max(1, int(total_income * RENT_TAX_RATE)) if total_income > 0 else 0
        receive_amount = total_income - tax

        if receive_amount < 0:
            receive_amount = 0

        user["money"] += receive_amount
        user["last_rent"] = now.strftime(DATETIME_FORMAT)

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="💰 임대료 수령 완료",
            description=(
                f"{interaction.user.mention}님이 임대료를 수령했어요.\n\n"
                f"{chr(10).join(detail_lines)}"
            ),
            color=discord.Color.gold()
        )
        embed.add_field(name="총 임대료", value=f"`{total_income:,} 코인`", inline=True)
        embed.add_field(name="세금 (5%)", value=f"`{tax:,} 코인`", inline=True)
        embed.add_field(name="실제 수령", value=f"`{receive_amount:,} 코인`", inline=True)
        embed.add_field(name="현재 재화", value=f"`{user['money']:,} 코인`", inline=False)
        embed.set_footer(text="임대료는 최대 24시간까지만 누적돼요.")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RealEstate(bot))