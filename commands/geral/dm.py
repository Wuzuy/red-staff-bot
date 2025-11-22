import discord
from discord.ext import commands
from utils.checks import has_admin_role
from database.database_manager import DB_FILE

class DM(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="dm")
    @commands.check(has_admin_role)
    async def dm(self, ctx: commands.Context, *, message: str):
        """Envia uma mensagem para todos os membros do servidor."""
        try:
            await ctx.message.delete()
        except discord.HTTPException: pass

        initial_embed = self.client.create_embed("Preparando Envio...", "Coletando membros e iniciando o processo. Esta mensagem será atualizada com o progresso.", 0x3498db)
        feedback_msg = await ctx.send(embed=initial_embed)
        
        # Chama a função centralizada para fazer o trabalho pesado
        await self.client.execute_dm_send(ctx.guild, message, ctx.author, feedback_msg)
        
    @dm.error
    async def dm_error(self, ctx: commands.Context, error):
        """Trata erros de sintaxe e permissão para o dm."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        if isinstance(error, commands.CheckFailure):
            embed = self.client.create_embed("Acesso Negado", f"{ctx.author.mention}, você não tem permissão para usar este comando.")
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.client.create_embed("Comando Inválido", f"Uso correto: `{ctx.prefix}{ctx.invoked_with} <mensagem>`")
            await ctx.send(embed=embed, delete_after=10)
        else:
            print(f"Erro em r.dm: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DM(client))
