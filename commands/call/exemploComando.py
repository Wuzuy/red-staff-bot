import discord
from discord.ext import commands

# Importa o check específico do core
from core import is_call_server

class CallCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="movcall")
    @is_call_server()
    async def mov_call_command(self, ctx: commands.Context):
        """Comando que só funciona nos servidores de call."""
        
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
            
        await ctx.send(
            f"Olá, {ctx.author.mention}! \n"
            f"Este é um comando exclusivo para servidores de Call.",
            delete_after=10
        )

    @mov_call_command.error
    async def mov_call_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            try:
                await ctx.message.delete() # Apenas deleta
            except discord.HTTPException:
                pass
        else:
            await ctx.send(
                f"{ctx.author.mention}, \n"
                f"Ocorreu um erro: {error}",
                delete_after=10
            )

async def setup(client: commands.Bot) -> None:
    await client.add_cog(CallCommands(client))
