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

        # Adicionar a lista de servidores
        guild_names = sorted([guild.name for guild in self.client.guilds])
        guild_list_str = ""
        for i, name in enumerate(guild_names):
            # Discord embed field value limit is 1024 characters
            # Leave some room for "..." and the count
            if len(guild_list_str) + len(name) + 2 > 1000:
                guild_list_str += f"\n... e mais {len(guild_names) - i} servidores."
                break
            guild_list_str += f"{name}\n"
        
        if not guild_list_str: # Fallback if no guilds or all names are too long
            guild_list_str = "Nenhum servidor encontrado ou lista muito longa para exibir."
        else:
            guild_list_str = guild_list_str.strip() # Remove trailing newline

        embed.add_field(name="Servidores Atuais", value=guild_list_str, inline=False)
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