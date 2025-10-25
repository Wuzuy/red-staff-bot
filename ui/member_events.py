import discord
from discord.ext import commands
from datetime import datetime, timezone

class MemberEvents(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self.client.create_embed("Log: Membro Entrou", "", 0x2ecc71)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Conta Criada em", value=discord.utils.format_dt(member.created_at, style='F'), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="entrada")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = self.client.create_embed("Log: Membro Saiu", "", 0xe74c3c)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Cargos", value=" ".join([r.mention for r in member.roles if not r.is_default()]) or "Nenhum", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="saida")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Log de Cargos
        roles_before = set(before.roles)
        roles_after = set(after.roles)

        added_roles = roles_after - roles_before
        removed_roles = roles_before - roles_after

        if added_roles:
            embed = self.client.create_embed("Log: Cargo Adicionado", "", 0x3498db)
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="Cargo Adicionado", value=" ".join([r.mention for r in added_roles]), inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="cargos")

        if removed_roles:
            embed = self.client.create_embed("Log: Cargo Removido", "", 0xe67e22)
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="Cargo Removido", value=" ".join([r.mention for r in removed_roles]), inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="cargos")

async def setup(client: commands.Bot):
    await client.add_cog(MemberEvents(client))