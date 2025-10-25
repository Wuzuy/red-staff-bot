import discord
from discord.ext import commands
from utils.checks import has_admin_role

class DMCargos(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="dmcargos", aliases=["dmconfig"])
    @commands.check(has_admin_role)
    async def dmcargos(self, ctx: commands.Context):
        """Abre um painel para configurar quais cargos recebem DMs em massa."""
        await self.client.delete_message_user(ctx)

        # Instancia a view do core.py
        view = self.client.DmConfigView(author=ctx.author, bot_instance=self.client, guild=ctx.guild)
        
        # Gera o embed inicial e envia a mensagem
        initial_embed = await view.generate_embed()
        await ctx.send(embed=initial_embed, view=view, delete_after=900) # Apaga após 15 minutos

    @dmcargos.error
    async def dmcargos_error(self, ctx: commands.Context, error):
        """Trata erros para o comando dmcargos."""
        try:
            # Tenta deletar a mensagem original do comando
            await self.client.delete_message_user(ctx)
        except discord.HTTPException:
            pass

        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.",
                delete_after=10
            )
        else:
            print(f"Erro inesperado no comando dmcargos: {error}")
            # Opcional: notificar o usuário sobre um erro genérico

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DMCargos(client))