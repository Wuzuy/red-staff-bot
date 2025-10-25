import discord
from discord.ext import commands
from utils.checks import is_super_admin

class DMAll(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="dmall")
    @commands.check(is_super_admin) 
    async def dmall(self, ctx: commands.Context, *, message: str):
        """Envia uma DM para todos os membros únicos em todos os servidores do bot."""
        try:
            await ctx.message.delete()
        except discord.HTTPException: pass
        
        feedback_embed = self.client.create_embed("Envio Global Iniciado", "O envio da sua mensagem foi iniciado em segundo plano. Relatórios serão enviados nos canais de logs quando for concluído.")
        await ctx.send(embed=feedback_embed, delete_after=20)
        
        # Chama a função centralizada
        await self.client.execute_dmall_send(message, ctx.author)

    @dmall.error
    async def dmall_error(self, ctx: commands.Context, error):
        """Trata erros para o comando r.dmall."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.\n"
                f"Apenas Super Admins do bot podem usar este comando.",
                delete_after=10
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention}, parâmetros do comando inválido.\n"
                f"Tente: `r.dmall <mensagem>`",
                delete_after=10
            )
        else:
            print(f"Erro em r.dmall: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DMAll(client))
