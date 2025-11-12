import discord
from discord.ext import commands
from utils.checks import is_super_admin
import asyncio

class Invite(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="invite", aliases=["invites"])
    @commands.dm_only()
    @commands.check(is_super_admin)
    async def invite(self, ctx: commands.Context):
        """
        Cria um convite único de 30 minutos para todos os servidores do bot.
        """
        embed = self.client.create_embed(
            "Convites dos Servidores",
            "Gerando convites para todos os servidores...",
            color=discord.Color.blurple()
        )
        msg = await ctx.send(embed=embed)

        invite_lines = []
        for guild in self.client.guilds:
            invite_link = "Não foi possível criar o convite (sem permissão ou canais)."
            for channel in guild.text_channels:
                # Tenta criar um convite no primeiro canal que tiver permissão
                if channel.permissions_for(guild.me).create_instant_invite:
                    try:
                        invite = await channel.create_invite(max_age=1800, max_uses=1, unique=True, reason=f"Convite solicitado por {ctx.author}")
                        invite_link = invite.url
                        break # Convite criado com sucesso, para de procurar canais
                    except Exception as e:
                        print(f"Erro ao criar convite para {guild.name}: {e}")
                        invite_link = f"Erro ao criar convite: {e}"
                        break
            invite_lines.append(f"**{guild.name}**: {invite_link}")

        final_embed = self.client.create_embed(
            "Convites dos Servidores",
            "\n".join(invite_lines) or "O bot não está em nenhum servidor.",
            color=discord.Color.green()
        )
        await msg.edit(embed=final_embed)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Invite(client))