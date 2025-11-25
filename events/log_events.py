import discord
from discord.ext import commands
import asyncio
from config import DEVELOPER_ID, DEVELOPER_ROLE_NAME

class LogEvents(commands.Cog, name="Eventos de Log"):
    """Cog para lidar com todos os eventos de log do servidor."""
    def __init__(self, client: commands.Bot):
        self.client = client

    async def _find_audit_log_entry(self, guild: discord.Guild, target_id: int, action: discord.AuditLogAction):
        """Busca a entrada no log de auditoria para uma ação específica e retorna o autor."""
        await asyncio.sleep(1.5) # Espera para garantir que o log de auditoria seja escrito
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target.id == target_id:
                    # Evita que a própria pessoa seja marcada como moderadora (ex: apagar a própria msg)
                    if entry.user.id != target_id:
                        return entry.user
        except (discord.Forbidden, discord.HTTPException):
            pass # Ignora se não tiver permissão
        return None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await asyncio.sleep(1)

        moderator = None
        # No log de auditoria, o 'target' para message_delete é o autor da mensagem
        moderator = await self._find_audit_log_entry(message.guild, message.author.id, discord.AuditLogAction.message_delete)

        embed = self.client.create_embed("Log: Mensagem Apagada", f"Mensagem de {message.author.mention} foi apagada.", 0xe74c3c)
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Autor", value=message.author.mention, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        if moderator:
            embed.add_field(name="Apagada por", value=moderator.mention, inline=True)
        if message.content:
            embed.add_field(name="Conteúdo", value=f"```\n{message.content[:1000]}\n```", inline=False)
        if message.attachments:
            embed.add_field(name="Anexos", value="\n".join([f.filename for f in message.attachments]), inline=False)

        await self.client.log_to_channel(message.guild, embed, log_type="mensagem")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content: return

        embed = self.client.create_embed("Log: Mensagem Editada", f"[Ir para a mensagem]({after.jump_url})", 0xf1c40f)
        embed.set_author(name=f"{after.author.name} ({after.author.id})", icon_url=after.author.display_avatar.url)
        embed.add_field(name="Autor", value=after.author.mention, inline=False)
        embed.add_field(name="Canal", value=before.channel.mention, inline=False)
        if before.content:
            embed.add_field(name="Antes", value=f"```\n{before.content[:1000]}\n```", inline=False)
        if after.content:
            embed.add_field(name="Depois", value=f"```\n{after.content[:1000]}\n```", inline=False)

        await self.client.log_to_channel(before.guild, embed, log_type="mensagem")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self.client.create_embed("Log: Membro Entrou", "", 0x2ecc71)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Usuário", value=member.mention, inline=False)
        embed.add_field(name="Conta Criada em", value=discord.utils.format_dt(member.created_at, style='F'), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="entrada")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        moderator = None
        log_type = "saida"
        log_title = "📤 Membro Saiu"
        color = 0xffa500 # Laranja

        # Verifica se foi uma expulsão (kick)
        kick_entry = await self._find_audit_log_entry(member.guild, member.id, discord.AuditLogAction.kick)
        if kick_entry:
            moderator = kick_entry.user
            log_type = "expulsao"
            log_title = "👢 Membro Expulso"
            color = 0xf39c12 # Laranja mais escuro

        # Verifica se foi um banimento
        ban_entry = await self._find_audit_log_entry(member.guild, member.id, discord.AuditLogAction.ban)
        if ban_entry:
            moderator = ban_entry.user
            log_type = "banimento"
            log_title = "🔨 Membro Banido"
            color = 0x000000 # Preto

        # Se for um banimento, não logamos a saída para evitar duplicidade
        if log_type == "banimento": return

        embed = self.client.create_embed(log_title, "", color)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        
        embed.add_field(name="Usuário", value=member.mention, inline=False)

        if moderator:
            embed.add_field(name="Moderador", value=moderator.mention, inline=True)

        roles_text = " ".join([r.mention for r in member.roles if not r.is_default()]) or "Nenhum"
        embed.add_field(name="Cargos", value=roles_text, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type=log_type)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return # Ignora outras atualizações de membro (nick, etc.)

        moderator = None
        moderator = await self._find_audit_log_entry(after.guild, after.id, discord.AuditLogAction.member_role_update)
        roles_before = set(before.roles)
        roles_after = set(after.roles)

        added_roles = roles_after - roles_before
        removed_roles = roles_before - roles_after

        # --- Verificação de exclusividade do cargo de Desenvolvedor ---
        developer_role = discord.utils.get(after.guild.roles, name=DEVELOPER_ROLE_NAME)

        # Verifica se o cargo "Desenvolvedor" foi adicionado indevidamente a um não-desenvolvedor
        if after.id != DEVELOPER_ID and developer_role and developer_role in added_roles:
            try:
                # Remove o cargo do membro imediatamente
                await after.remove_roles(developer_role, reason="Cargo exclusivo do desenvolvedor.")
                print(f"Removido cargo '{DEVELOPER_ROLE_NAME}' indevidamente atribuído a {after.name} ({after.id}) em '{after.guild.name}'.")
                # Remove o cargo da lista de 'added_roles' para não logar a adição indevida
                added_roles.remove(developer_role)
            except discord.Forbidden:
                print(f"Falha ao remover cargo '{DEVELOPER_ROLE_NAME}' de {after.name} em '{after.guild.name}' (sem permissão).")
        # --- Fim da verificação ---

        moderator_mention = moderator.mention if moderator else "Não identificado"

        if added_roles:
            embed = self.client.create_embed("Log: Cargo Adicionado", "", 0x3498db)
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="Usuário", value=after.mention, inline=False)
            embed.add_field(name="Cargo Adicionado", value=" ".join([r.mention for r in added_roles]), inline=False)
            embed.add_field(name="Moderador", value=moderator_mention, inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="cargos")

        if removed_roles:
            embed = self.client.create_embed("Log: Cargo Removido", "", 0xe67e22)
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="Usuário", value=after.mention, inline=False)
            embed.add_field(name="Cargo Removido", value=" ".join([r.mention for r in removed_roles]), inline=False)
            embed.add_field(name="Moderador", value=moderator_mention, inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="cargos")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        moderator = await self._find_audit_log_entry(channel.guild, channel.id, discord.AuditLogAction.channel_create)

        embed = self.client.create_embed("Log: Canal Criado", "", 0x2ecc71)
        embed.add_field(name="Canal", value=channel.mention, inline=False)
        if moderator:
            embed.add_field(name="Criado por", value=moderator.mention, inline=False)
        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        moderator = await self._find_audit_log_entry(channel.guild, channel.id, discord.AuditLogAction.channel_delete)

        embed = self.client.create_embed("Log: Canal Deletado", "", 0xe74c3c)
        embed.add_field(name="Nome", value=f"`{channel.name}`", inline=True)
        if moderator:
            embed.add_field(name="Deletado por", value=moderator.mention, inline=True)
        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name != after.name:
            moderator = await self._find_audit_log_entry(after.guild, after.id, discord.AuditLogAction.channel_update)

            embed = self.client.create_embed("Log: Canal Renomeado", "", 0xf1c40f)
            embed.add_field(name="Canal", value=after.mention, inline=False)
            embed.add_field(name="Nome Antigo", value=f"`{before.name}`", inline=True)
            embed.add_field(name="Nome Novo", value=f"`{after.name}`", inline=True)
            if moderator:
                embed.add_field(name="Renomeado por", value=moderator.mention, inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="canal")

    # --- LOGS DE CARGOS ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        moderator = await self._find_audit_log_entry(role.guild, role.id, discord.AuditLogAction.role_create)

        embed = self.client.create_embed("Log: Cargo Criado", "", 0x2ecc71)
        embed.add_field(name="Cargo", value=role.mention, inline=False)
        if moderator:
            embed.add_field(name="Criado por", value=moderator.mention, inline=False)
        await self.client.log_to_channel(role.guild, embed, log_type="cargos")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        moderator = await self._find_audit_log_entry(role.guild, role.id, discord.AuditLogAction.role_delete)

        embed = self.client.create_embed("Log: Cargo Deletado", "", 0xe74c3c)
        embed.add_field(name="Nome do Cargo", value=f"`{role.name}`", inline=False)
        if moderator:
            embed.add_field(name="Deletado por", value=moderator.mention, inline=False)
        await self.client.log_to_channel(role.guild, embed, log_type="cargos")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name == after.name: return # Ignora mudanças de cor, permissão, etc. por enquanto

        moderator = await self._find_audit_log_entry(after.guild, after.id, discord.AuditLogAction.role_update)

        embed = self.client.create_embed("Log: Cargo Renomeado", "", 0xf1c40f)
        embed.add_field(name="Cargo", value=after.mention, inline=False)
        embed.add_field(name="Nome Antigo", value=f"`{before.name}`", inline=True)
        embed.add_field(name="Nome Novo", value=f"`{after.name}`", inline=True)
        if moderator:
            embed.add_field(name="Renomeado por", value=moderator.mention, inline=False)
        await self.client.log_to_channel(after.guild, embed, log_type="cargos")

    # --- LOGS DE BANIMENTO ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await self._find_audit_log_entry(guild, user.id, discord.AuditLogAction.ban)
        moderator = entry.user if entry else "Não encontrado"
        reason = entry.reason if entry and entry.reason else "Nenhum motivo fornecido."

        embed = self.client.create_embed("🔨 Membro Banido", "", 0x000000)
        embed.add_field(name="Usuário", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="Moderador", value=moderator.mention if isinstance(moderator, discord.User) else moderator, inline=True)
        embed.add_field(name="Motivo", value=reason, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await self.client.log_to_channel(guild, embed, log_type="banimento")

async def setup(client: commands.Bot):
    await client.add_cog(LogEvents(client))