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

        initial_embed = self.client.create_embed("Preparando Envio Global...", "Coletando membros e iniciando o processo. Esta mensagem será atualizada com o progresso.", 0x3498db)
        feedback_msg = await ctx.send(embed=initial_embed)
        
        # Chama a função centralizada
        await self.client.execute_dmall_send(message, ctx.author, feedback_msg)

    @dmall.error
    async def dmall_error(self, ctx: commands.Context, error):
        """Trata erros para o comando r.dmall."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if isinstance(error, commands.CheckFailure):
            embed = self.client.create_embed("Acesso Negado", f"{ctx.author.mention}, apenas Super Admins podem usar este comando.")
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.client.create_embed("Comando Inválido", f"Uso correto: `{ctx.prefix}{ctx.invoked_with} <mensagem>`")
            await ctx.send(embed=embed, delete_after=10)
        else:
            print(f"Erro em r.dmall: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DMAll(client))
