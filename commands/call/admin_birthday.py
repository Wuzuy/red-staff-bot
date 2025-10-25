import discord
from discord.ext import commands
from utils.checks import has_admin_role, is_call_server

class Admin(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="admin")
    @is_call_server()
    @commands.check(has_admin_role)
    async def admin(self, ctx: commands.Context):
        """Abre o painel de administração do bot."""
        await self.client.delete_message_user(ctx)

        embed = self.client.create_user_embed(ctx.author, ctx.guild, "Selecione uma opção para gerenciar.\n\n> **Aniversários:** Adicione, remova ou altere aniversários no servidor.", title="Painel de Administração")
        view = self.client.AdminBirthdayManagementView(author=ctx.author, bot_instance=self.client, guild=ctx.guild)
        await ctx.send(embed=embed, view=view, delete_after=900) # Apaga após 15 minutos

    @admin.error
    async def admin_error(self, ctx: commands.Context, error):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando ou ele não pode ser usado neste servidor.",
                delete_after=10
            )
        else:
            print(f"Erro no comando r.admin: {error}")
            await ctx.send(f"{ctx.author.mention}, ocorreu um erro ao executar o comando.", delete_after=10)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Admin(client))