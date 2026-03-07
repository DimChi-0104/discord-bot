import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta, timezone

DATA_FILE = "data/economy.json"
KST = timezone(timedelta(hours=9))

MIN_REWARD = 100
MAX_REWARD = 300
MAX_STREAK_BONUS = 100

MIN_TRANSFER = 10
MAX_TRANSFER = 100000
MAX_ADMIN_AMOUNT = 100000000


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


class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="출석", description="하루 1회 출석하고 재화를 받습니다.")
    async def attendance(self, interaction: discord.Interaction):
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
        today = now.strftime("%Y-%m-%d")

        if user["last_attendance"] == today:
            next_day = datetime(now.year, now.month, now.day, tzinfo=KST) + timedelta(days=1)
            remain = next_day - now
            total_seconds = max(0, int(remain.total_seconds()))
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            embed = discord.Embed(
                title="이미 출석 완료",
                description=(
                    "오늘은 이미 출석했어요.\n"
                    f"다음 출석까지: `{hours}시간 {minutes}분`"
                ),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        if user["last_attendance"] == yesterday:
            user["streak"] += 1
        else:
            user["streak"] = 1

        base_reward = random.randint(MIN_REWARD, MAX_REWARD)
        streak_bonus = min(user["streak"] * 10, MAX_STREAK_BONUS)
        total_reward = base_reward + streak_bonus

        user["money"] += total_reward
        user["last_attendance"] = today
        user["total_attendance"] += 1

        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="출석 완료",
            description=(
                f"{interaction.user.mention}님의 오늘 출석이 완료되었어요.\n\n"
                f"기본 지급: `{base_reward} 코인`\n"
                f"연속 출석 보너스: `{streak_bonus} 코인`\n"
                f"총 획득: `{total_reward} 코인`\n\n"
                f"현재 보유 재화: `{user['money']} 코인`\n"
                f"연속 출석: `{user['streak']}일`\n"
                f"총 출석 횟수: `{user['total_attendance']}회`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="지갑", description="현재 보유한 재화를 확인합니다.")
    async def wallet(self, interaction: discord.Interaction, 대상: discord.Member = None):
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

        target = 대상 or interaction.user

        if target.bot:
            await interaction.response.send_message(
                "봇 계정의 지갑은 확인할 수 없어요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, target.id)
        save_data(data)

        embed = discord.Embed(
            title="지갑 정보",
            description=(
                f"대상: {target.mention}\n"
                f"보유 재화: `{user['money']} 코인`\n"
                f"연속 출석: `{user['streak']}일`\n"
                f"총 출석 횟수: `{user['total_attendance']}회`\n"
                f"도박 전적: `{user['win']}승 / {user['lose']}패`"
            ),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="재화랭킹", description="서버 내 재화 랭킹을 확인합니다.")
    async def money_ranking(self, interaction: discord.Interaction):
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

            money = info.get("money", 0)
            if not isinstance(money, int):
                money = 0
            if money < 0:
                money = 0

            ranking.append((member, money))

        ranking.sort(key=lambda x: x[1], reverse=True)
        top_10 = ranking[:10]

        if not top_10:
            await interaction.response.send_message(
                "아직 등록된 유저 데이터가 없어요.",
                ephemeral=True
            )
            return

        lines = []
        medals = ["🥇", "🥈", "🥉"]

        for idx, (member, money) in enumerate(top_10, start=1):
            prefix = medals[idx - 1] if idx <= 3 else f"{idx}위"
            lines.append(f"{prefix} {member.display_name} - `{money} 코인`")

        embed = discord.Embed(
            title="재화 랭킹 TOP 10",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="송금", description="다른 유저에게 재화를 송금합니다.")
    @app_commands.checks.cooldown(1, 3.0)
    async def transfer(
        self,
        interaction: discord.Interaction,
        대상: discord.Member,
        금액: int
    ):
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

        if 대상.bot:
            await interaction.response.send_message(
                "봇에게는 송금할 수 없어요.",
                ephemeral=True
            )
            return

        if 대상.id == interaction.user.id:
            await interaction.response.send_message(
                "자기 자신에게는 송금할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 < MIN_TRANSFER:
            await interaction.response.send_message(
                f"송금 금액은 최소 `{MIN_TRANSFER}`코인 이상이어야 해요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_TRANSFER:
            await interaction.response.send_message(
                f"송금 금액은 최대 `{MAX_TRANSFER}`코인까지 가능해요.",
                ephemeral=True
            )
            return

        data = load_data()

        sender = get_user_data(data, interaction.user.id)
        receiver = get_user_data(data, 대상.id)

        if sender["money"] < 금액:
            await interaction.response.send_message(
                f"보유 재화가 부족해요.\n현재 보유 재화: `{sender['money']} 코인`",
                ephemeral=True
            )
            return

        sender["money"] -= 금액
        receiver["money"] += 금액

        if sender["money"] < 0:
            sender["money"] = 0

        if receiver["money"] < 0:
            receiver["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="송금 완료",
            description=(
                f"보낸 사람: {interaction.user.mention}\n"
                f"받는 사람: {대상.mention}\n"
                f"송금 금액: `{금액} 코인`\n\n"
                f"내 현재 보유 재화: `{sender['money']} 코인`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="재화지급", description="유저에게 재화를 지급합니다. (관리자 전용)")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_money(
        self,
        interaction: discord.Interaction,
        대상: discord.Member,
        금액: int
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if 대상.bot:
            await interaction.response.send_message(
                "봇 계정에는 재화를 지급할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 <= 0:
            await interaction.response.send_message(
                "지급 금액은 1 이상이어야 해요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_ADMIN_AMOUNT:
            await interaction.response.send_message(
                f"한 번에 지급할 수 있는 최대 금액은 `{MAX_ADMIN_AMOUNT}`코인이에요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, 대상.id)

        user["money"] += 금액
        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="재화 지급 완료",
            description=(
                f"관리자: {interaction.user.mention}\n"
                f"대상: {대상.mention}\n"
                f"지급 금액: `{금액} 코인`\n"
                f"현재 보유 재화: `{user['money']} 코인`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="재화차감", description="유저의 재화를 차감합니다. (관리자 전용)")
    @app_commands.checks.has_permissions(administrator=True)
    async def take_money(
        self,
        interaction: discord.Interaction,
        대상: discord.Member,
        금액: int
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if 대상.bot:
            await interaction.response.send_message(
                "봇 계정의 재화는 차감할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 <= 0:
            await interaction.response.send_message(
                "차감 금액은 1 이상이어야 해요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_ADMIN_AMOUNT:
            await interaction.response.send_message(
                f"한 번에 차감할 수 있는 최대 금액은 `{MAX_ADMIN_AMOUNT}`코인이에요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, 대상.id)

        user["money"] -= 금액
        if user["money"] < 0:
            user["money"] = 0

        save_data(data)

        embed = discord.Embed(
            title="재화 차감 완료",
            description=(
                f"관리자: {interaction.user.mention}\n"
                f"대상: {대상.mention}\n"
                f"차감 금액: `{금액} 코인`\n"
                f"현재 보유 재화: `{user['money']} 코인`"
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="재화설정", description="유저의 재화를 원하는 값으로 설정합니다. (관리자 전용)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_money(
        self,
        interaction: discord.Interaction,
        대상: discord.Member,
        금액: int
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "이 명령어는 서버에서만 사용할 수 있어요.",
                ephemeral=True
            )
            return

        if 대상.bot:
            await interaction.response.send_message(
                "봇 계정의 재화는 설정할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 < 0:
            await interaction.response.send_message(
                "재화는 0 미만으로 설정할 수 없어요.",
                ephemeral=True
            )
            return

        if 금액 > MAX_ADMIN_AMOUNT:
            await interaction.response.send_message(
                f"설정 가능한 최대 금액은 `{MAX_ADMIN_AMOUNT}`코인이에요.",
                ephemeral=True
            )
            return

        data = load_data()
        user = get_user_data(data, 대상.id)

        user["money"] = 금액

        save_data(data)

        embed = discord.Embed(
            title="재화 설정 완료",
            description=(
                f"관리자: {interaction.user.mention}\n"
                f"대상: {대상.mention}\n"
                f"설정 금액: `{금액} 코인`\n"
                f"현재 보유 재화: `{user['money']} 코인`"
            ),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Attendance(bot))