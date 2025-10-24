import discord
from discord.ext import commands
from utils.checks import is_super_admin 

class ConfigPerm(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(
        name="configperm",
        help="Abre um painel para configurar os cargos de admin do bot."
    )
    @commands.check(is_super_admin)
    async def configperm(self, ctx: commands.Context):
        """Abre um painel para configurar os cargos de admin do bot."""
        await self.client.delete_message_user(ctx)

        view = self.client.ConfigPermView(author=ctx.author, guild=ctx.guild)
        initial_embed = await view.generate_embed()
        await ctx.send(embed=initial_embed, view=view, delete_after=900) # Apaga após 15 minutos

    @configperm.error
    async def configperm_error(self, ctx: commands.Context, error):
        """Trata erros para o comando configperm."""
        await self.client.delete_message_user(ctx)
        
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, apenas Super Admins podem usar este comando.",
                delete_after=10
            )
        else:
            print(f"Erro inesperado no comando configperm: {error}")

async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConfigPerm(client))
