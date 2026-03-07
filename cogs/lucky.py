import datetime
import json
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

DATA_FILE = "data/daily_data.json"
PI_FILE = "pi_100000.txt"
QUOTES_FILE = "quotes.txt"


def ensure_data_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_data():
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data):
    ensure_data_file()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def can_use(user_id: int, command_name: str) -> bool:
    today = str(datetime.date.today())
    data = load_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {}

    if command_name not in data[user_id] or data[user_id][command_name] != today:
        data[user_id][command_name] = today
        save_data(data)
        return True
    return False


def load_quotes():
    if not os.path.exists(QUOTES_FILE):
        return [("오늘도 좋은 하루 보내세요.", "디모")]

    quotes = []
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                text, author = line.split("|", maxsplit=1)
                quotes.append((text.strip(), author.strip()))
            else:
                quotes.append((line, "출처 없음"))

    return quotes or [("오늘도 좋은 하루 보내세요.", "디모")]


def load_pi_digits():
    if not os.path.exists(PI_FILE):
        return "314159265358979323846264338327950288419716939937510"
    with open(PI_FILE, "r", encoding="utf-8") as f:
        return f.read().replace("\n", "")


PI_DIGITS = load_pi_digits()
QUOTES = load_quotes()


class Lucky(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="오늘의운세", description="오늘 하루 운세와 명언을 확인합니다. (하루 1회)")
    @app_commands.checks.cooldown(1, 10.0)
    async def today_fortune(self, interaction: discord.Interaction):
        if not can_use(interaction.user.id, "today_fortune"):
            return await interaction.response.send_message(
                f"⏳ {interaction.user.display_name}님은 이미 오늘 운세를 확인하셨습니다!"
            )

        lucky_number = random.choice(PI_DIGITS)
        luck_percent = random.randint(1, 100)

        if luck_percent <= 30:
            message = "☁️ 오늘은 조금 조심하세요."
            color = discord.Color.red()
        elif luck_percent <= 70:
            message = "🌤️ 무난한 하루가 될 거예요."
            color = discord.Color.gold()
        else:
            message = "☀️ 행운이 가득한 하루네요!"
            color = discord.Color.green()

        text, author = random.choice(QUOTES)

        embed = discord.Embed(title="🍀 오늘의 운세 🍀", color=color)
        embed.add_field(name="행운의 숫자", value=f"`{lucky_number}`", inline=True)
        embed.add_field(name="행운 수치", value=f"`{luck_percent}%`", inline=True)
        embed.add_field(name="오늘의 메시지", value=message, inline=False)
        embed.add_field(name="오늘의 명언", value=f"_{text}_\n- **{author}**", inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} | {datetime.date.today()}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="오늘의메뉴", description="오늘 뭐 먹을지 랜덤 추천!")
    async def today_menu(self, interaction: discord.Interaction):
        menus = [
            "🍜 짜장면", "🍕 피자", "🍔 햄버거", "🍗 치킨", "🍣 초밥",
            "🍖 삼겹살", "🍝 파스타", "🌮 타코", "🍱 돈카츠", "🍧 빙수",
            "🧇 크로플", "🍜 라멘", "🥩 스테이크", "🥗 샐러드"
        ]

        choice = random.choice(menus)

        embed = discord.Embed(
            title="🍽️ 오늘의 메뉴 추천",
            description=f"{interaction.user.display_name}님께 추천!\n\n**{choice}**",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="딤치의생일알아보기", description="딤치의 생일과 D-Day를 알려줍니다!")
    async def dimchi_birthday(self, interaction: discord.Interaction):
        dimchi_id = 662509817234980895
        dimchi = await self.bot.fetch_user(dimchi_id)

        today = datetime.date.today()
        birthday = datetime.date(today.year, 1, 4)
        if birthday < today:
            birthday = datetime.date(today.year + 1, 1, 4)

        d_day = (birthday - today).days

        if d_day == 0:
            d_text = "🎉 오늘은 딤치의 생일입니다!!! 🎉"
        else:
            d_text = f"📅 생일까지 D-{d_day}일 남았습니다!"

        embed = discord.Embed(
            title="🎂 딤치의 생일 정보",
            description=f"딤치의 생일은 **1월 4일** 입니다!\n\n{d_text}",
            color=discord.Color.blue()
        )

        avatar_url = dimchi.avatar.url if dimchi.avatar else dimchi.default_avatar.url
        embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text=f"요청자: {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Lucky(bot))