import discord
from discord.ext import commands
import sqlite3
import asyncio
from utils.checks import is_super_admin
from database.database_manager import DB_FILE

class DmDev(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def _get_all_admins(self) -> set[discord.User | discord.Member]:
        """Coleta um conjunto de todos os usuários administradores e super admins únicos."""
        admin_users = set()

        # Adiciona Super Admins
        for admin_id in self.client.super_admin_ids:
            user = await self.client.fetch_user(admin_id)
            if user:
                admin_users.add(user)

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            for guild in self.client.guilds:
                # Busca cargos de admin configurados para o servidor
                cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (guild.id,))
                admin_role_ids = {row[0] for row in cursor.fetchall()}

                for member in guild.members:
                    if member.bot:
                        continue
                    
                    # Verifica permissão nativa de admin do Discord
                    if member.guild_permissions.administrator:
                        admin_users.add(member)
                        continue
                    
                    # Verifica se o membro possui algum dos cargos de admin configurados
                    if admin_role_ids:
                        member_role_ids = {role.id for role in member.roles}
                        if not member_role_ids.isdisjoint(admin_role_ids):
                            admin_users.add(member)
        
        return admin_users

    @commands.command(name="dmdev", help="Envia um aviso para todos os admins e devs do bot.")
    @commands.check(is_super_admin)
    async def dmdev(self, ctx: commands.Context, *, message: str):
        """Envia um aviso em DM para todos os administradores e desenvolvedores do bot."""
        await self.client.delete_message_user(ctx)
        
        feedback_msg = await ctx.send("🔍 Coletando todos os administradores... Isso pode levar um momento.")

        admins_to_dm = await self._get_all_admins()
        
        await feedback_msg.edit(content=f"✅ {len(admins_to_dm)} administradores encontrados. Iniciando o envio das DMs...")

        embed = discord.Embed(
            title="📢 Aviso para Desenvolvedores/Administradores",
            description=message,
            color=self.client.default_color
        )
        embed.set_footer(text=f"Enviado por: {ctx.author.display_name}")

        success_count = 0
        fail_count = 0

        for admin in admins_to_dm:
            try:
                await admin.send(embed=embed)
                success_count += 1
            except (discord.Forbidden, discord.HTTPException):
                fail_count += 1
            await asyncio.sleep(1) # Evitar rate limits

        await feedback_msg.edit(content=f"🏁 Envio concluído!\n\n- **Sucessos:** `{success_count}`\n- **Falhas:** `{fail_count}`", delete_after=60)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(DmDev(client))