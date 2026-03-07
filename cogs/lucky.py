import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import json
import os

DATA_FILE = "daily_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE,"w") as f:
            json.dump({},f)
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f)

class Lucky(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="오늘의메뉴")
    async def menu(self, interaction: discord.Interaction):

        menus = ["짜장면","치킨","피자","햄버거","초밥","삼겹살","파스타"]
        choice = random.choice(menus)

        embed = discord.Embed(
            title="🍽 오늘의 메뉴",
            description=f"추천 메뉴: **{choice}**"
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="오늘의운세")
    async def fortune(self, interaction: discord.Interaction):

        luck = random.randint(1,100)

        embed = discord.Embed(
            title="🍀 오늘의 운세",
            description=f"행운 수치: **{luck}%**"
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Lucky(bot))