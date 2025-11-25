import discord
from discord.ext import commands
from datetime import datetime
import asyncio

class MemberLogs(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Listener para quando um membro entra no servidor.
        Envia um log para o canal configurado em 'log_join_channel_id'.
        """
        if member.bot:
            return

        log_channel = await self.client.get_log_channel(member.guild, "entrada")
        if not log_channel:
            return

        embed = self.client.create_embed(
            title="📥 Membro Entrou",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Membro", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Conta Criada em", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)
        embed.set_footer(text=f"ID do Usuário: {member.id}")

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        Listener para quando um membro sai do servidor.
        Envia um log para o canal configurado em 'log_leave_channel_id'.
        """
        if member.bot:
            return

        log_channel = await self.client.get_log_channel(member.guild, "saida")
        if not log_channel:
            return

        embed = self.client.create_embed(
            title="📤 Membro Saiu",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Membro", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.set_footer(text=f"ID do Usuário: {member.id}")

        await log_channel.send(embed=embed)

async def setup(client: commands.Bot):
    await client.add_cog(MemberLogs(client))