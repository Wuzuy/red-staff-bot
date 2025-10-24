import discord
from discord.ext import commands


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if 1+1 > 2:
            return

async def setup(bot):
    await bot.add_cog(OnMessage(bot))
