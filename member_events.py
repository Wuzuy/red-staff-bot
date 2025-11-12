import discord
from discord.ext import commands

class MemberEventsCog(commands.Cog, name="MemberEvents"):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Garante o cargo de desenvolvedor se for o usuário específico
        if member.id == DEVELOPER_ID:
            await self.client.ensure_developer_role()

        embed = self.client.create_embed("Log: Membro Entrou", "", 0x2ecc71)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Conta Criada em", value=discord.utils.format_dt(member.created_at, style='F'), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="entrada")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Este listener é apenas para o log de saída.
        # A lógica de remover aniversário está em events/birthday_events.py
        embed = self.client.create_embed("Log: Membro Saiu", "", 0xe74c3c)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        
        roles_text = " ".join([r.mention for r in member.roles if not r.is_default()]) or "Nenhum"
        embed.add_field(name="Cargos", value=roles_text, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="saida")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # --- Verificação de exclusividade do cargo de Desenvolvedor ---
        DEV_ID = DEVELOPER_ID
        ROLE_NAME = "Desenvolvedor"

        # Log de Cargos
        roles_before = set(before.roles)
        roles_after = set(after.roles)

        added_roles = roles_after - roles_before
        removed_roles = roles_before - roles_after

        developer_role = discord.utils.get(after.guild.roles, name=ROLE_NAME)

        # Verifica se o cargo "Desenvolvedor" foi adicionado indevidamente
        if after.id != DEV_ID and developer_role and developer_role in added_roles:
            try:
                # Remove o cargo do membro
                await after.remove_roles(developer_role, reason="Cargo exclusivo do desenvolvedor.")
                print(f"Removido cargo '{ROLE_NAME}' indevidamente atribuído a {after.name} ({after.id}) em '{after.guild.name}'.")
                # Remove o cargo da lista de 'added_roles' para não logar a adição
                added_roles.remove(developer_role)
            except discord.Forbidden:
                print(f"Falha ao remover cargo '{ROLE_NAME}' de {after.name} em '{after.guild.name}' (sem permissão).")

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
    await client.add_cog(MemberEventsCog(client))