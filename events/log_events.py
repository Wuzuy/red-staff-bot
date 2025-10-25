import discord
from discord.ext import commands
import asyncio

class LogEvents(commands.Cog, name="Eventos de Log"):
    """Cog para lidar com todos os eventos de log do servidor."""
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await asyncio.sleep(1)

        moderator = None
        try:
            async for entry in message.guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
                if entry.extra.channel.id == message.channel.id and entry.target.id == message.author.id:
                    if entry.user.id != message.author.id:
                        moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {message.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria: {e}")

        embed = self.client.create_embed("Log: Mensagem Apagada", f"Mensagem de {message.author.mention} foi apagada.", 0xe74c3c)
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Autor", value=message.author.mention, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=False)
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
        reason = None
        log_title = "Log: Membro Saiu"

        await asyncio.sleep(1) # Aguarda o log de auditoria
        try:
            # Verifica se foi uma expulsão
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    moderator = entry.user
                    reason = entry.reason
                    log_title = "Log: Membro Expulso"
                    break
            
            if not moderator:
                async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                    if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                        moderator = entry.user
                        reason = entry.reason
                        log_title = "Log: Membro Banido"
                        break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {member.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_member_remove: {e}")

        embed = self.client.create_embed(log_title, "", 0xe74c3c)
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        
        embed.add_field(name="Usuário", value=member.mention, inline=False)

        if moderator:
            embed.add_field(name="Moderador", value=moderator.mention, inline=True)
        if reason:
            embed.add_field(name="Motivo", value=reason, inline=True)

        roles_text = " ".join([r.mention for r in member.roles if not r.is_default()]) or "Nenhum"
        embed.add_field(name="Cargos", value=roles_text, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.client.log_to_channel(member.guild, embed, log_type="saida")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return # Ignora outras atualizações de membro (nick, etc.)

        moderator = None
        await asyncio.sleep(1) # Aguarda o log de auditoria
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {after.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_member_update: {e}")

        roles_before = set(before.roles)
        roles_after = set(after.roles)

        added_roles = roles_after - roles_before
        removed_roles = roles_before - roles_after

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
        moderator = None
        await asyncio.sleep(1)
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {channel.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_guild_channel_create: {e}")

        embed = self.client.create_embed("Log: Canal Criado", "", 0x2ecc71)
        embed.add_field(name="Canal", value=channel.mention, inline=False)
        if moderator:
            embed.add_field(name="Criado por", value=moderator.mention, inline=False)

        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        moderator = None
        await asyncio.sleep(1)
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {channel.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_guild_channel_delete: {e}")

        embed = self.client.create_embed("Log: Canal Deletado", "", 0xe74c3c)
        embed.add_field(name="Nome", value=f"`{channel.name}`", inline=True)
        if moderator:
            embed.add_field(name="Deletado por", value=moderator.mention, inline=True)

        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name != after.name:
            moderator = None
            await asyncio.sleep(1)
            try:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                    if entry.target.id == after.id:
                        moderator = entry.user
                        break
            except Exception: pass

            embed = self.client.create_embed("Log: Canal Renomeado", "", 0xf1c40f)
            embed.add_field(name="Canal", value=after.mention, inline=False)
            embed.add_field(name="Nome Antigo", value=f"`{before.name}`", inline=True)
            embed.add_field(name="Nome Novo", value=f"`{after.name}`", inline=True)
            if moderator:
                embed.add_field(name="Renomeado por", value=moderator.mention, inline=False)
            await self.client.log_to_channel(after.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        moderator = None
        await asyncio.sleep(1)
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {role.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_guild_role_create: {e}")

        embed = self.client.create_embed("Log: Cargo Criado", "", 0x2ecc71)
        embed.add_field(name="Cargo", value=role.mention, inline=False)
        if moderator:
            embed.add_field(name="Criado por", value=moderator.mention, inline=False)
        
        await self.client.log_to_channel(role.guild, embed, log_type="cargos")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        moderator = None
        await asyncio.sleep(1)
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id:
                    moderator = entry.user
                    break
        except discord.Forbidden:
            print(f"Sem permissão para ver o log de auditoria no servidor: {role.guild.name}")
        except Exception as e:
            print(f"Erro ao acessar o log de auditoria para on_guild_role_delete: {e}")

        embed = self.client.create_embed("Log: Cargo Deletado", "", 0xe74c3c)
        embed.add_field(name="Nome do Cargo", value=f"`{role.name}`", inline=False)
        if moderator:
            embed.add_field(name="Deletado por", value=moderator.mention, inline=False)

        await self.client.log_to_channel(role.guild, embed, log_type="cargos")

async def setup(client: commands.Bot):
    await client.add_cog(LogEvents(client))