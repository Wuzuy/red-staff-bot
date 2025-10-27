import discord
from discord.ext import commands
from utils.checks import is_super_admin

class BotInfo(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="botinfo", help="Mostra informações sobre o bot e sua abrangência.")
    @commands.check(is_super_admin)
    async def botinfo(self, ctx: commands.Context):
        """
        Exibe o número de servidores em que o bot está e o total de membros únicos que ele pode alcançar.
        """
        await self.client.delete_message_user(ctx)

        # Contar servidores
        guild_count = len(self.client.guilds)

        # Contar membros únicos
        unique_members = set()
        for guild in self.client.guilds:
            for member in guild.members:
                if not member.bot: # Excluir bots
                    unique_members.add(member.id)
        
        member_count = len(unique_members)

        embed = self.client.create_embed(
            "Informações do Bot",
            f"O bot está atualmente em `{guild_count}` servidores.\n"
            f"Ele pode alcançar `{member_count}` membros únicos com DMs globais."
        )
        embed.add_field(name="Super Admins", value=", ".join([f"<@{sa_id}>" for sa_id in self.client.super_admin_ids]), inline=False)
        embed.set_thumbnail(url=self.client.user.display_avatar.url)
        
        await ctx.send(embed=embed, delete_after=60) # Apaga após 1 minuto

    @botinfo.error
    async def botinfo_error(self, ctx: commands.Context, error):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{ctx.author.mention}, você não tem permissão para usar este comando.\nApenas Super Admins do bot podem usar este comando.", delete_after=10)
        else:
            print(f"Erro em r.botinfo: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(BotInfo(client))