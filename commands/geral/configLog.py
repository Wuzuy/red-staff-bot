import discord
from discord.ext import commands
import sqlite3
from database.database_manager import DB_FILE
from utils.checks import has_admin_role 

class ConfigLog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(
        name="configlog",
        help="Configura o canal de logs para o servidor."
    )
    @commands.check(has_admin_role) 
    async def configlog(self, ctx: commands.Context, canal: discord.TextChannel):
        """Define o canal de logs, salvando no banco de dados."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        guild_id = ctx.guild.id

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO server_configs (guild_id, log_channel_id) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id
            """, (guild_id, canal.id))
            conn.commit()

        embed = self.client.create_user_embed(
            ctx.author,
            ctx.guild,
            f"O canal de log foi definido com sucesso para {canal.mention}.",
            color=0x2ecc71
        )
        view = self.client.create_deletable_message_view(ctx.author)
        await ctx.send(embed=embed, view=view)

    @configlog.error
    async def configlog_error(self, ctx: commands.Context, error):
        """Trata erros de sintaxe e permissão para o configlog."""
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
                f"{ctx.author.mention}, você esqueceu de mencionar o canal.\n"
                f"**Sintaxe correta:** `r.configlog #canal`",
                delete_after=10
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{ctx.author.mention}, não consegui encontrar o canal de texto que você mencionou.\n"
                f"**Sintaxe correta:** `r.configlog #canal`",
                delete_after=10
            )
        else:
            print(f"Erro em r.configlog: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConfigLog(client))
