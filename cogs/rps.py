import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

RECORD_FILE = "rps_records.json"

def load_records():
    if not os.path.exists(RECORD_FILE):
        with open(RECORD_FILE,"w") as f:
            json.dump({},f)
    with open(RECORD_FILE) as f:
        return json.load(f)

def save_records(data):
    with open(RECORD_FILE,"w") as f:
        json.dump(data,f,indent=4)

class RPS(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="가위바위보")
    async def rps(self, interaction: discord.Interaction):

        choices = ["가위","바위","보"]
        bot_choice = random.choice(choices)

        await interaction.response.send_message(f"봇 선택: **{bot_choice}**")

async def setup(bot):
    await bot.add_cog(RPS(bot))