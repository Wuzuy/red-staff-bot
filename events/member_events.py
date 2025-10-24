import discord
from discord.ext import commands
import sqlite3
from database.database_manager import DB_FILE
import config

class MemberEvents(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove o aniversário de um membro se ele sair do servidor."""
        if member.guild.id not in config.CALL_SERVERS_IDS:
            return # Apenas remove aniversários em servidores de call

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?", (member.guild.id, member.id))
            if cursor.rowcount > 0: # Se um aniversário foi removido
                conn.commit()

                # Log da ação
                log_description = (
                    f"**Ação:** Aniversário Removido (Saída do Servidor)\n"
                    f"**Usuário:** {member.mention} (`{member.id}`)"
                )
                log_embed = self.client.create_user_embed(
                    self.client.user, member.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0x95a5a6
                )
                await self.client.log_to_channel(member.guild, log_embed)

                await self.client._update_birthday_message(member.guild.id)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(MemberEvents(client))