import discord
import sqlite3
from database.database_manager import DB_FILE
from .base_view import BaseView

class DmConfigView(BaseView):
    """View interativa para configurar quais cargos recebem DMs em massa."""

    def __init__(self, author: discord.User, bot_instance, guild: discord.Guild):
        super().__init__(author=author, timeout=900.0) # 15 minutos
        self.bot_instance = bot_instance
        self.guild = guild

    async def generate_embed(self) -> discord.Embed:
        """Gera e retorna o embed com a lista atual de cargos."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM dm_roles WHERE guild_id = ?", (self.guild.id,))
            role_ids = [row[0] for row in cursor.fetchall()]

        description = "Abaixo estão os cargos configurados para receber DMs em massa.\nSe nenhum cargo for listado, **todos** os membros do servidor receberão as mensagens.\n\n"
        if not role_ids:
            description += "**Nenhum cargo configurado.**"
        else:
            roles_mentions = []
            for role_id in role_ids:
                role = self.guild.get_role(role_id)
                if role:
                    roles_mentions.append(role.mention)
            description += " ".join(roles_mentions) if roles_mentions else "Nenhum cargo encontrado (podem ter sido deletados)."

        return self.bot_instance.create_user_embed(
            self.author, self.guild, description, title="Configuração de Cargos para DM"
        )

    async def update_message(self, interaction: discord.Interaction):
        """Atualiza a mensagem com o novo embed e a view atual."""
        new_embed = await self.generate_embed()
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.RoleSelect(placeholder="Selecione os cargos para adicionar...", min_values=1, max_values=25)
        
        async def select_callback(select_interaction: discord.Interaction):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for role in select.values:
                    cursor.execute("INSERT OR IGNORE INTO dm_roles (guild_id, role_id) VALUES (?, ?)", (self.guild.id, role.id))
                conn.commit()
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM dm_roles WHERE guild_id = ?", (self.guild.id,))
            role_ids = [row[0] for row in cursor.fetchall()]

        if not role_ids:
            await interaction.response.send_message("Não há cargos para remover.", ephemeral=True)
            return

        options = [discord.SelectOption(label=role.name, value=str(role.id)) for role_id in role_ids if (role := self.guild.get_role(role_id))]
        select = discord.ui.Select(placeholder="Selecione os cargos para remover...", min_values=1, max_values=len(options), options=options)

        async def select_callback(select_interaction: discord.Interaction):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for role_id in select.values:
                    cursor.execute("DELETE FROM dm_roles WHERE guild_id = ? AND role_id = ?", (self.guild.id, int(role_id)))
                conn.commit()
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Adicionar Todos", style=discord.ButtonStyle.secondary, emoji="✅", row=1)
    async def add_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            all_roles = [role for role in self.guild.roles if not role.is_default()] # Exclui @everyone
            for role in all_roles:
                cursor.execute("INSERT OR IGNORE INTO dm_roles (guild_id, role_id) VALUES (?, ?)", (self.guild.id, role.id))
            conn.commit()
        await self.update_message(interaction)

    @discord.ui.button(label="Remover Todos", style=discord.ButtonStyle.secondary, emoji="❌", row=1)
    async def remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dm_roles WHERE guild_id = ?", (self.guild.id,))
            conn.commit()
        await self.update_message(interaction)

class ConfigPermView(BaseView):
    """View interativa para configurar os cargos de admin do bot."""

    def __init__(self, author: discord.User, bot_instance, guild: discord.Guild):
        super().__init__(author=author, timeout=900.0) # 15 minutos
        self.bot_instance = bot_instance
        self.guild = guild

    async def generate_embed(self) -> discord.Embed:
        """Gera e retorna o embed com a lista atual de cargos de admin."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (self.guild.id,))
            role_ids = [row[0] for row in cursor.fetchall()]

        description = "Abaixo estão os cargos com permissão de administrador do bot neste servidor.\n\n"
        if not role_ids:
            description += "**Nenhum cargo de admin configurado.**"
        else:
            roles_mentions = [role.mention for role_id in role_ids if (role := self.guild.get_role(role_id))]
            description += " ".join(roles_mentions) if roles_mentions else "Nenhum cargo encontrado (podem ter sido deletados)."

        return self.bot_instance.create_user_embed(
            self.author, self.guild, description, title="Configuração de Permissões de Admin"
        )

    async def update_message(self, interaction: discord.Interaction):
        """Atualiza a mensagem com o novo embed e a view atual."""
        new_embed = await self.generate_embed()
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="✅")
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.RoleSelect(placeholder="Selecione os cargos para adicionar...", min_values=1, max_values=25)
        
        async def select_callback(select_interaction: discord.Interaction):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for role in select.values:
                    cursor.execute("INSERT OR IGNORE INTO perm_roles (guild_id, role_id) VALUES (?, ?)", (self.guild.id, role.id))
                conn.commit()
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM perm_roles WHERE guild_id = ?", (self.guild.id,))
            role_ids = [row[0] for row in cursor.fetchall()]

        if not role_ids:
            await interaction.response.send_message("Não há cargos para remover.", ephemeral=True)
            return

        options = [discord.SelectOption(label=role.name, value=str(role.id)) for role_id in role_ids if (role := self.guild.get_role(role_id))]
        if not options:
            await interaction.response.send_message("Não há cargos válidos para remover.", ephemeral=True)
            return
            
        select = discord.ui.Select(placeholder="Selecione os cargos para remover...", min_values=1, max_values=len(options), options=options)

        async def select_callback(select_interaction: discord.Interaction):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for role_id in select.values:
                    cursor.execute("DELETE FROM perm_roles WHERE guild_id = ? AND role_id = ?", (self.guild.id, int(role_id)))
                conn.commit()
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remover Todos", style=discord.ButtonStyle.secondary, emoji="❌")
    async def remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM perm_roles WHERE guild_id = ?", (self.guild.id,))
            conn.commit()
        await self.update_message(interaction)