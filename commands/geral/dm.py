import sqlite3
import discord
from discord.ext import commands
import asyncio
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
        except discord.HTTPException:
            pass
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM dm_roles WHERE guild_id = ?", (ctx.guild.id,))
            allowed_role_ids = {row[0] for row in cursor.fetchall()}
        
        members_to_dm = []
        if not allowed_role_ids:
            # Comportamento padrão: todos os membros
            members_to_dm = [m for m in ctx.guild.members if not m.bot]
        else:
            # Filtra membros que possuem pelo menos um dos cargos permitidos
            for member in ctx.guild.members:
                if not member.bot and any(role.id in allowed_role_ids for role in member.roles):
                    members_to_dm.append(member)
        total_members = len(members_to_dm)

        status_embed = self.client.create_embed("Envio em Massa Iniciado", f"Preparando para enviar mensagem para {total_members} membros.")
        status_message = await ctx.send(embed=status_embed)

        successful_members = []
        failed_members = []
        message_dm = f"# <:red1:1431082037900738620><:red2:1431082036147523725>\n\n{message}"

        for i, member in enumerate(members_to_dm):
            try:
                await member.send(message_dm)
                successful_members.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_members.append(member)
            
            success_count, fail_count = len(successful_members), len(failed_members)
            
            if (i + 1) % 10 == 0 or (i + 1) == total_members:
                progress_embed = self.client.create_embed("Envio em Andamento", "", 0xf1c40f)
                progress_embed.add_field(name="Progresso:", value=f"{i + 1}/{total_members} membros.", inline=False)
                progress_embed.add_field(name="Sucessos:", value=f"`{success_count}`", inline=True)
                progress_embed.add_field(name="Falhas:", value=f"`{fail_count}`", inline=True)
                await status_message.edit(embed=progress_embed)
            
            await asyncio.sleep(5.0)

        final_embed = self.client.create_embed("Relatório de Envio de DM", "Processo concluído!", 0x2ecc71)
        final_embed.add_field(name="Membros Alcançados", value=f"`{success_count}`", inline=True)
        final_embed.add_field(name="Falhas (DMs fechadas)", value=f"`{fail_count}`", inline=True)
        await status_message.edit(embed=final_embed)
        await status_message.delete(delay=15)
        
        log_embed = self.client.create_embed("Log: Envio de DM em Massa", "", 0xffa500)
        log_embed.add_field(name="Autor", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Alcançados", value=f"`{len(successful_members)}`", inline=True)
        log_embed.add_field(name="Falhas", value=f"`{len(failed_members)}`", inline=True)
        log_embed.add_field(name="Mensagem", value=f"```\n{message}\n```", inline=False)

        # Cria a view do log com as listas de membros
        log_view = self.client.DmLogView(
            author=ctx.author, successful_members=successful_members, failed_members=failed_members
        )
        await self.client.log_to_channel(ctx.guild, log_embed, view=log_view)
        
    @dm.error
    async def dm_error(self, ctx: commands.Context, error):
        """Trata erros de sintaxe e permissão para o dm."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.\n"
                f"Apenas administradores ou cargos configurados podem usar.",
                delete_after=10
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention}, parâmetros do comando inválido.\n"
                f"Tente: `r.dm <mensagem>`",
                delete_after=10
            )
        else:
            print(f"Erro em r.dm: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DM(client))
