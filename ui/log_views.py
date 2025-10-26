import discord
import io
import sqlite3
from database.database_manager import DB_FILE
from .base_view import BaseView

class DmLogView(BaseView):
    """View para os logs de DM, com botões para ver listas de sucesso e falha."""
    def __init__(self, author: discord.User, successful_members: list, failed_members: list):
        super().__init__(author=author, timeout=None) # A view no log não expira
        self.successful_members = successful_members
        self.failed_members = failed_members
        
        # Desabilita botões se as listas estiverem vazias
        if not self.successful_members:
            self.show_success.disabled = True
        if not self.failed_members:
            self.show_failures.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Permite que qualquer administrador do servidor interaja com esta view,
        não apenas o autor original.
        """
        # Super Admins sempre podem interagir
        if interaction.user.id in interaction.client.super_admin_ids:
            return True

        # Verifica se o usuário tem cargo de admin no servidor
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (interaction.guild_id,))
            admin_role_ids = {row[0] for row in cursor.fetchall()}

        # Se não houver cargos configurados, verifica a permissão de Administrador do Discord
        if not admin_role_ids:
            if interaction.user.guild_permissions.administrator:
                return True
        # Se houver cargos, verifica se o usuário possui algum deles
        elif any(role.id in admin_role_ids for role in interaction.user.roles):
            return True

        await interaction.response.send_message("Apenas administradores podem ver os detalhes deste log.", ephemeral=True)
        return False

    async def _send_members_file(self, interaction: discord.Interaction, members: list, filename: str, title: str):
        """Gera um arquivo de texto e o envia de forma efêmera."""
        if not members:
            await interaction.response.send_message(f"Não há membros na lista '{title}'.", ephemeral=True)
            return

        # Cria o conteúdo do arquivo
        content = "\n".join([f"{member.name} ({member.id})" for member in members])
        file_bytes = io.BytesIO(content.encode('utf-8'))
        
        file = discord.File(file_bytes, filename=filename)
        await interaction.response.send_message(f"Aqui está a lista de **{title}**:", file=file, ephemeral=True)

    @discord.ui.button(label="Ver Sucessos", style=discord.ButtonStyle.success)
    async def show_success(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_members_file(interaction, self.successful_members, "sucessos.txt", "Membros Alcançados")

    @discord.ui.button(label="Ver Falhas", style=discord.ButtonStyle.danger)
    async def show_failures(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_members_file(interaction, self.failed_members, "falhas.txt", "Falhas de Envio")