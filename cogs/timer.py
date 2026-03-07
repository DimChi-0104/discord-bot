from discord.ext import commands

class Timer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def 타이머(self, ctx):
        await ctx.send("타이머 작동!")

async def setup(bot):
    await bot.add_cog(Timer(bot))