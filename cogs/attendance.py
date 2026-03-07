import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
DATA_FILE = "data/economy.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        os.makedirs("data", exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}}, f, ensure_ascii=False, indent=4)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_user_data(data, user_id: int):
    user_id = str(user_id)
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "money": 0,
            "last_attendance": "",
            "streak": 0,
            "total_attendance": 0,
            "win": 0,
            "lose": 0
        }
    return data["users"][user_id]


class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="출석", description="하루 1회 출석하고 재화를 받습니다.")
    async def attendance(self, interaction: discord.Interaction):
        data = load_data()
        user = get_user_data(data, interaction.user.id)

        today = datetime.now(KST).strftime("%Y-%m-%d")
        now = datetime.now(KST)

        if user["last_attendance"] == today:
            next_day = datetime(now.year, now.month, now.day, tzinfo=KST) + timedelta(days=1)
            remain = next_day - now
            hours, remainder = divmod(int(remain.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            await interaction.response.send_message(
                f"이미 오늘 출석했어요.\n다음 출석까지: `{hours}시간 {minutes}분`",
                ephemeral=True
            )
            return

        yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
        if user["last_attendance"] == yesterday:
            user["streak"] += 1
        else:
            user["streak"] = 1

        reward = random.randint(100, 300)
        streak_bonus = min(user["streak"] * 10, 100)
        total_reward = reward + streak_bonus

        user["money"] += total_reward
        user["last_attendance"] = today
        user["total_attendance"] += 1

        save_data(data)

        embed = discord.Embed(
            title="출석 완료",
            description=(
                f"기본 지급: `{reward} 코인`\n"
                f"연속 출석 보너스: `{streak_bonus} 코인`\n"
                f"총 획득: `{total_reward} 코인`\n\n"
                f"현재 보유 재화: `{user['money']} 코인`\n"
                f"연속 출석: `{user['streak']}일`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="지갑", description="현재 보유한 재화를 확인합니다.")
    async def wallet(self, interaction: discord.Interaction, 대상: discord.Member = None):
        data = load_data()
        target = 대상 or interaction.user
        user = get_user_data(data, target.id)

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
        data = load_data()
        users = data.get("users", {})

        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get("money", 0),
            reverse=True
        )[:10]

        if not sorted_users:
            await interaction.response.send_message("아직 등록된 유저 데이터가 없어요.", ephemeral=True)
            return

        lines = []
        for idx, (user_id, info) in enumerate(sorted_users, start=1):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"알 수 없음({user_id})"
            lines.append(f"**{idx}.** {name} - `{info.get('money', 0)} 코인`")

        embed = discord.Embed(
            title="재화 랭킹 TOP 10",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Attendance(bot))