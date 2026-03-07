import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN이 .env에 설정되어 있지 않습니다.")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

async def load_extensions():
    for folder in ("core", "cogs"):
        if not os.path.isdir(folder):
            continue

        for file in os.listdir(folder):
            if not file.endswith(".py"):
                continue
            if file in ("__init__.py", "cog_loader.py"):
                continue

            ext = f"{folder}.{file[:-3]}"

            try:
                await bot.load_extension(ext)
                print(f"[COG] {file[:-3]} 로드")
            except Exception as e:
                print(f"[ERROR] {file[:-3]} -> {e}")

@bot.event
async def on_ready():
    guild = discord.Object(id=1479777711013761107)

    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)

    print(f"[SYNC] 테스트 서버 동기화 완료 ({len(synced)}개)")
    print(f"[READY] {bot.user}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())