import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta, timezone

DATA_FILE = "data/economy.json"
KST = timezone(timedelta(hours=9))

WORK_COOLDOWN = timedelta(minutes=30)
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

MIN_WORK_REWARD = 250
MAX_WORK_REWARD = 600

BONUS_CHANCE = 0.10
BONUS_MIN_REWARD = 700
BONUS_MAX_REWARD = 1000


WORK_MESSAGES = [
    "편의점 야간 근무를 하고",
    "카페 아르바이트를 하고",
    "배달 일을 하고",
    "행사 스태프로 일하고",
    "창고 정리 알바를 하고",
    "사무 보조 일을 하고",
    "전단지 배포를 하고",
    "매장 진열 보조를 하고"
]

BONUS_MESSAGES = [
    "야간 정산 업무를 완벽하게 처리해서",
    "급한 추가 근무를 맡아 성공적으로 끝내서",
    "행사 진행을 도와 큰 보너스를 받아서",
    "특별 의뢰를 완수해서",
    "사장님의 긴급 부탁을 해결해서"
]


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
        fallback = {"users": {}}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(fallback, f, ensure_ascii=False, indent=4)
        return fallback


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
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=KST)
        except ValueError:
            continue

    return None


def get_user_data(data, user_id: int):
    user_id = str(user_id)

    if user_id not in data["users"] or not isinstance(data["users"][user_id], dict):
        data["users"][user_id] = {}

    user = data["users"][user_id]

    defaults = {
        "money": 0,
        "last_attendance": "",
        "last_work": "",
        "streak": 0,
        "total_attendance": 0,
        "win": 0,
        "lose": 0,
        "slot_win": 0,
        "slot_lose": 0,
        "inventory": {},
        "titles": [],
        "active_effects": {
            "luck": 0,
            "title_create": 0,
            "nickname_change": 0
        },
        "title_data": {
            "name": "",
            "color": "#FFFFFF"
        }
    }

    for key, value in defaults.items():
        if key not in user or not isinstance(user[key], type(value)):
            user[key] = value

    if "inventory" not in user or not isinstance(user["inventory"], dict):
        user["inventory"] = {}

    if "titles" not in user or not isinstance(user["titles"], list):
        user["titles"] = []

    if "active_effects" not in user or not isinstance(user["active_effects"], dict):
        user["active_effects"] = {
            "luck": 0,
            "title_create": 0,
            "nickname_change": 0
        }

    user["active_effects"].setdefault("luck", 0)
    user["active_effects"].setdefault("title_create", 0)
    user["active_effects"].setdefault("nickname_change", 0)

    if "title_data" not in user or not isinstance(user["title_data"], dict):
        user["title_data"] = {
            "name": "",
            "color": "#FFFFFF"
        }

    user["title_data"].setdefault("name", "")
    user["title_data"].setdefault("color", "#FFFFFF")

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
    if user["slot_win"] < 0:
        user["slot_win"] = 0
    if user["slot_lose"] < 0:
        user["slot_lose"] = 0

    return user


class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="일하기", description="30분마다 일을 해서 재화를 벌어요.")
    async def work(self, interaction: discord.Interaction):
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

        now = datetime.now(KST)
        last_work_dt = parse_datetime(user.get("last_work", ""))

        if last_work_dt is not None:
            next_work_dt = last_work_dt + WORK_COOLDOWN

            if now < next_work_dt:
                remain = next_work_dt - now
                total_seconds = max(0, int(remain.total_seconds()))
                minutes, seconds = divmod(total_seconds, 60)

                embed = discord.Embed(
                    title="💼 아직 다시 일할 수 없어요",
                    description=(
                        f"다음 일하기 가능 시간: `{next_work_dt.strftime('%Y-%m-%d %H:%M:%S')} (KST)`\n"
                        f"남은 시간: `{minutes}분 {seconds}초`"
                    ),
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        is_bonus = random.random() < BONUS_CHANCE

        if is_bonus:
            reward = random.randint(BONUS_MIN_REWARD, BONUS_MAX_REWARD)
            work_text = random.choice(BONUS_MESSAGES)
            result_title = "💎 특별 보너스 발생!"
            color = discord.Color.gold()
        else:
            reward = random.randint(MIN_WORK_REWARD, MAX_WORK_REWARD)
            work_text = random.choice(WORK_MESSAGES)
            result_title = "💼 일하기 완료"
            color = discord.Color.green()

        user["money"] += reward
        user["last_work"] = now.strftime(DATETIME_FORMAT)

        if user["money"] < 0:
            user["money"] = 0

        next_work_dt = now + WORK_COOLDOWN
        save_data(data)

        embed = discord.Embed(
            title=result_title,
            description=(
                f"{interaction.user.mention}님이 {work_text}\n"
                f"`{reward:,} 코인`을 벌었어요.\n\n"
                f"현재 보유 재화: `{user['money']:,} 코인`\n"
                f"다음 일하기 가능 시간: `{next_work_dt.strftime('%Y-%m-%d %H:%M:%S')} (KST)`"
            ),
            color=color
        )

        if is_bonus:
            embed.set_footer(text="운이 좋아서 높은 보상을 받았어요!")
        else:
            embed.set_footer(text="30분 후 다시 /일하기 를 사용할 수 있어요.")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Work(bot))