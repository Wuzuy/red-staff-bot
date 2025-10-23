import discord
from discord.ext import commands
import sqlite3
from utils.checks import is_super_admin 
from database.database_manager import DB_FILE

class ConfigPerm(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.group(
        name="configperm",
        help="Configura os cargos de admin do bot neste servidor.",
        invoke_without_command=True
    )
    @commands.check(is_super_admin)
    async def configperm(self, ctx: commands.Context):
        """Mostra a ajuda do comando configperm."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        await ctx.send(
            f"{ctx.author.mention}, \n"
            f"Use `r.configperm add @cargo` ou `r.configperm remove @cargo`.",
            delete_after=15
        )

    @configperm.command(name="add")
    @commands.check(is_super_admin)
    async def configperm_add(self, ctx: commands.Context, role: discord.Role):
        """Adiciona um cargo à lista de admins do bot."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
            
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO perm_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id))
                conn.commit()
                embed = self.client.create_user_embed(ctx.author, ctx.guild, f"O cargo {role.mention} agora pode usar os comandos de admin.", color=0x2ecc71)
                await ctx.send(embed=embed, view=self.client.create_deletable_message_view(ctx.author))
            except sqlite3.IntegrityError: 
                embed = self.client.create_user_embed(ctx.author, ctx.guild, f"O cargo {role.mention} já tem permissão.", color=0xffa500)
                await ctx.send(embed=embed, view=self.client.create_deletable_message_view(ctx.author))

    @configperm.command(name="remove")
    @commands.check(is_super_admin)
    async def configperm_remove(self, ctx: commands.Context, role: discord.Role):
        """Remove um cargo da lista de admins do bot."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
            
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM perm_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id))
            conn.commit()
        
        if cursor.rowcount > 0:
            embed = self.client.create_user_embed(ctx.author, ctx.guild, f"O cargo {role.mention} não pode mais usar os comandos de admin.", color=0x2ecc71)
            await ctx.send(embed=embed, view=self.client.create_deletable_message_view(ctx.author))
        else:
            embed = self.client.create_user_embed(ctx.author, ctx.guild, f"O cargo {role.mention} não tinha permissão.", color=0xffa500)
            await ctx.send(embed=embed, view=self.client.create_deletable_message_view(ctx.author))

    # Tratador de erro para o grupo 'configperm'
    @configperm.error
    async def configperm_error(self, ctx: commands.Context, error):
        """Trata erros de sintaxe e permissão para o grupo configperm."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        # Respostas de ERRO usam texto simples (ctx.send)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.\n"
                f"Apenas Super Admins do bot podem configurá-lo.",
                delete_after=10
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention}, você esqueceu de um argumento.\n"
                f"**Sintaxe correta:** `r.configperm <add|remove> @cargo`",
                delete_after=10
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{ctx.author.mention}, não consegui encontrar o cargo que você mencionou.\n"
                f"**Sintaxe correta:** `r.configperm <add|remove> @cargo`",
                delete_after=10
            )
        else:
            print(f"Erro em r.configperm: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConfigPerm(client))
