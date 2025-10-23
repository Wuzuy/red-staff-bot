import asyncio
import discord
from discord.ext import commands
from utils.checks import is_super_admin
import sqlite3
from database.database_manager import DB_FILE

class DMAll(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="dmall")
    @commands.check(is_super_admin) 
    async def dmall(self, ctx: commands.Context, *, message: str):
        """Envia uma DM para todos os membros únicos em todos os servidores do bot."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT guild_id, role_id FROM dm_roles")
            # Cria um dicionário: {guild_id: {role_id1, role_id2, ...}}
            guild_to_roles = {}
            for guild_id, role_id in cursor.fetchall():
                if guild_id not in guild_to_roles:
                    guild_to_roles[guild_id] = set()
                guild_to_roles[guild_id].add(role_id)

        unique_members = set()
        for guild in self.client.guilds:
            allowed_roles = guild_to_roles.get(guild.id)
            if not allowed_roles:
                # Se o servidor não tem cargos configurados, adiciona todos os membros
                for member in guild.members:
                    if not member.bot:
                        unique_members.add(member)
            else:
                # Se tem cargos, adiciona apenas membros com esses cargos
                for member in guild.members:
                    if not member.bot and any(role.id in allowed_roles for role in member.roles):
                        unique_members.add(member)

        total_unique = len(unique_members)
        
        status_embed = self.client.create_embed("Envio Global Iniciado", f"Preparando para enviar a mensagem para {total_unique} membros únicos.", 0xe74c3c)
        status_message = await ctx.send(embed=status_embed)

        success_count, fail_count = 0, 0
        message_to_send = f"**Mensagem de {self.client.user.name}**\n{message}"

        for i, member in enumerate(unique_members):
            try:
                await member.send(message_to_send)
                success_count += 1
            except (discord.Forbidden, discord.HTTPException):
                fail_count += 1
            
            if (i + 1) % 10 == 0 or (i + 1) == total_unique:
                progress_embed = self.client.create_embed("Envio Global em Andamento...", "", 0xf1c40f)
                progress_embed.add_field(name="Progresso:", value=f"{i + 1}/{total_unique}", inline=False)
                progress_embed.add_field(name="Sucessos:", value=f"`{success_count}`", inline=True)
                progress_embed.add_field(name="Falhas:", value=f"`{fail_count}`", inline=True)
                await status_message.edit(embed=progress_embed)
            
            await asyncio.sleep(2.0)
        
        final_embed = self.client.create_embed("Relatório de Envio Global", "Processo concluído!", 0x2ecc71)
        final_embed.add_field(name="Alcançados", value=f"`{success_count}`", inline=True)
        final_embed.add_field(name="Falhas", value=f"`{fail_count}`", inline=True)
        await status_message.edit(embed=final_embed)
        await status_message.delete(delay=15)

    @dmall.error
    async def dmall_error(self, ctx: commands.Context, error):
        """Trata erros para o comando r.dmall."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.\n"
                f"Apenas Super Admins do bot podem usar este comando.",
                delete_after=10
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention}, você esqueceu de escrever a mensagem.\n"
                f"**Sintaxe correta:** `r.dmall <mensagem>`",
                delete_after=10
            )
        else:
            print(f"Erro em r.dmall: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DMAll(client))
