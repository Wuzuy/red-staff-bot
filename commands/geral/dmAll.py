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

        unique_members = set()
        for guild in self.client.guilds:
            # Adiciona todos os membros (não-bots) de cada servidor ao conjunto.
            # O 'set' garante que cada membro seja contado apenas uma vez.
            for member in guild.members:
                if not member.bot:
                    unique_members.add(member)

        total_unique = len(unique_members)
        
        status_embed = self.client.create_embed("Envio Global Iniciado", f"Preparando para enviar a mensagem para {total_unique} membros únicos.", 0xe74c3c)
        status_message = await ctx.send(embed=status_embed)

        successful_members = []
        failed_members = []
        message_to_send = f"# <:red1:1431082037900738620><:red2:1431082036147523725>\n\n{message}"

        for i, member in enumerate(unique_members):
            try:
                await member.send(message_to_send)
                successful_members.append(member)
            except (discord.Forbidden, discord.HTTPException):
                failed_members.append(member)
            
            success_count, fail_count = len(successful_members), len(failed_members)
            if (i + 1) % 10 == 0 or (i + 1) == total_unique:
                progress_embed = self.client.create_embed("Envio Global em Andamento...", "", 0xf1c40f)
                progress_embed.add_field(name="Progresso:", value=f"{i + 1}/{total_unique}", inline=False)
                progress_embed.add_field(name="Sucessos:", value=f"`{success_count}`", inline=True)
                progress_embed.add_field(name="Falhas:", value=f"`{fail_count}`", inline=True)
                await status_message.edit(embed=progress_embed)
            
            await asyncio.sleep(5.0)
        
        final_embed = self.client.create_embed("Relatório de Envio Global", "Processo concluído!", 0x2ecc71)
        final_embed.add_field(name="Alcançados", value=f"`{success_count}`", inline=True)
        final_embed.add_field(name="Falhas", value=f"`{fail_count}`", inline=True)
        await status_message.edit(embed=final_embed)
        await status_message.delete(delay=15)

        # Envia o log para todos os canais de log configurados
        log_embed = self.client.create_embed("Log: Envio de DM Global", "", 0xffa500)
        log_embed.add_field(name="Autor", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Alcançados", value=f"`{len(successful_members)}`", inline=True)
        log_embed.add_field(name="Falhas", value=f"`{len(failed_members)}`", inline=True)
        log_embed.add_field(name="Mensagem", value=f"```\n{message}\n```", inline=False)

        log_view = self.client.DmLogView(
            author=ctx.author, successful_members=successful_members, failed_members=failed_members
        )
        for guild in self.client.guilds:
            await self.client.log_to_channel(guild, log_embed, view=log_view)

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
                f"{ctx.author.mention}, parâmetros do comando inválido.\n"
                f"Tente: `r.dmall <mensagem>`",
                delete_after=10
            )
        else:
            print(f"Erro em r.dmall: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DMAll(client))
