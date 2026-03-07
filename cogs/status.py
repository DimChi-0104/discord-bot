import discord
from discord.ext import commands, tasks
import itertools


class Status(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.status_list = itertools.cycle([
            "서버 관리를 도와주는 중",
            "/도움말",
            "디모 작동 중",
            "서버 관리 지원"
        ])

        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    @tasks.loop(seconds=20)
    async def status_loop(self):

        status = next(self.status_list)

        await self.bot.change_presence(
            activity=discord.Game(status)
        )

    @status_loop.before_loop
    async def before_status(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Status(bot))