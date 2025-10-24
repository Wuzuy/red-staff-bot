import discord
from discord.ext import commands
import os
import io
import sqlite3
from datetime import datetime, timezone

import config
from database.database_manager import initialize_database, DB_FILE
import discord.ui

# --- CHECAGENS DE PERMISSÃO (DECORATORS) ---

def is_call_server():
    async def predicate(ctx):
        return ctx.guild.id in config.CALL_SERVERS_IDS
    return commands.check(predicate)

def is_chat_server():
    async def predicate(ctx):
        return ctx.guild.id in config.CHAT_SERVERS_IDS
    return commands.check(predicate)


class RedCommunityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix="r.", intents=intents)
        
        self.super_admin_ids = config.SUPER_ADMIN_IDS

        # Cooldown
        self.global_cooldown = commands.CooldownMapping.from_cooldown(
            rate=1,
            per=3.0,
            type=commands.BucketType.user
        )

    # --- MÉTODO DE SETUP E EVENTOS ---

    async def setup_hook(self):
        """Encontra e carrega todas as extensões (cogs) automaticamente."""
        
        cogs_folders = ["commands", "events"] 
        
        for folder in cogs_folders:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        module_path = os.path.join(root, file)[:-3].replace(os.sep, '.')

                        try:
                            await self.load_extension(module_path)
                            print(f"Cog carregado: {module_path}")
                        except Exception as e:
                            print(f"Falha ao carregar o cog {module_path}: {e}")

    async def on_ready(self):
        """Evento executado quando o bot está online e pronto."""
        print(f'Bot conectado como {self.user}')
        initialize_database()

    # --- FUNÇÕES UTILITÁRIAS (MÉTODOS ESTÁTICOS) ---
    
    @staticmethod
    def create_embed(title, description, color=0xff0000):
        """Cria um objeto discord.Embed padronizado."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        return embed

    @staticmethod
    async def delete_message_user(ctx):
        """Deleta a mensagem que invocou um comando."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @staticmethod
    def create_user_embed(author: discord.User, guild: discord.Guild, description: str, *, title: str = "", color: int = 0xff0000) -> discord.Embed:
        """
        Cria um discord.Embed padronizado com o autor e servidor em destaque.
        Formato: "Nome do Servidor - Nome do Usuário"
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=f"{guild.name} - {author.display_name}", icon_url=author.display_avatar.url)
        return embed

    # --- COMPONENTES DE UI (VIEWS) ---

    class BaseView(discord.ui.View):
        """Uma View base que só permite a interação do autor original."""
        def __init__(self, author: discord.User, *, timeout: float = 180.0):
            super().__init__(timeout=timeout)
            self.author = author

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            """Verifica se o usuário que interagiu é o autor do comando."""
            if interaction.user.id != self.author.id:
                await interaction.response.send_message("Você não tem permissão para interagir com isso.", ephemeral=True)
                return False
            return True

    @staticmethod
    def create_deletable_message_view(author: discord.User, *, timeout: float = 180.0) -> discord.ui.View:
        """
        Cria uma View com um único botão para deletar a mensagem.
        Apenas o autor pode clicar.
        """
        view = RedCommunityBot.BaseView(author=author, timeout=timeout)

        # O botão pode ser definido como uma classe interna ou diretamente
        delete_button = discord.ui.Button(label="Apagar", style=discord.ButtonStyle.danger, emoji="🗑️")

        async def delete_callback(interaction: discord.Interaction):
            await interaction.message.delete()
        
        delete_button.callback = delete_callback
        view.add_item(delete_button)
        return view

    class DmConfigView(BaseView):
        """View interativa para configurar quais cargos recebem DMs em massa."""

        def __init__(self, author: discord.User, guild: discord.Guild):
            super().__init__(author=author, timeout=900.0) # 15 minutos
            self.guild = guild
            self.update_embed_callback = self.generate_embed # Atribuir a função para ser chamada

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

            return RedCommunityBot.create_user_embed(
                self.author, self.guild, description, title="Configuração de Cargos para DM"
            )

        async def update_message(self, interaction: discord.Interaction):
            """Atualiza a mensagem com o novo embed e a view atual."""
            new_embed = await self.generate_embed()
            await interaction.response.edit_message(embed=new_embed, view=self)

        @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="<:adicionar:EMOJI_ADICIONAR>", row=0)
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

        @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="<:remover:EMOJI_REMOVER>", row=0)
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

        @discord.ui.button(label="Adicionar Todos", style=discord.ButtonStyle.secondary, emoji="<:correto:EMOJI_CORRETO>", row=1)
        async def add_all(self, interaction: discord.Interaction, button: discord.ui.Button):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                all_roles = [role for role in self.guild.roles if not role.is_default()] # Exclui @everyone
                for role in all_roles:
                    cursor.execute("INSERT OR IGNORE INTO dm_roles (guild_id, role_id) VALUES (?, ?)", (self.guild.id, role.id))
                conn.commit()
            await self.update_message(interaction)

        @discord.ui.button(label="Remover Todos", style=discord.ButtonStyle.secondary, emoji="<:errado:EMOJI_ERRADO>", row=1)
        async def remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM dm_roles WHERE guild_id = ?", (self.guild.id,))
                conn.commit()
            await self.update_message(interaction)

    class ConfigPermView(BaseView):
        """View interativa para configurar os cargos de admin do bot."""

        def __init__(self, author: discord.User, guild: discord.Guild):
            super().__init__(author=author, timeout=900.0) # 15 minutos
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

            return RedCommunityBot.create_user_embed(
                self.author, self.guild, description, title="Configuração de Permissões de Admin"
            )

        async def update_message(self, interaction: discord.Interaction):
            """Atualiza a mensagem com o novo embed e a view atual."""
            new_embed = await self.generate_embed()
            await interaction.response.edit_message(embed=new_embed, view=self)

        @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="<:adicionar:EMOJI_ADICIONAR>")
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

        @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="<:remover:EMOJI_REMOVER>")
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

        @discord.ui.button(label="Remover Todos", style=discord.ButtonStyle.secondary, emoji="<:errado:EMOJI_ERRADO>")
        async def remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM perm_roles WHERE guild_id = ?", (self.guild.id,))
                conn.commit()
            await self.update_message(interaction)

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

        @discord.ui.button(label="Ver Sucessos", style=discord.ButtonStyle.success, emoji="<:correto:EMOJI_CORRETO>")
        async def show_success(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self._send_members_file(interaction, self.successful_members, "sucessos.txt", "Membros Alcançados")

        @discord.ui.button(label="Ver Falhas", style=discord.ButtonStyle.danger, emoji="<:errado:EMOJI_ERRADO>")
        async def show_failures(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self._send_members_file(interaction, self.failed_members, "falhas.txt", "Falhas de Envio")


    # --- MÉTODO PARA LOGS ---

    async def log_to_channel(self, guild: discord.Guild, embed: discord.Embed, *, view: discord.ui.View = None):
        """Busca o canal de log no DB e envia o embed."""
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT log_channel_id FROM server_configs WHERE guild_id = ?", (guild.id,))
            result = cursor.fetchone()

        if result and result[0]:
            log_channel_id = result[0]
            log_channel = self.get_channel(log_channel_id)
            
            if log_channel:
                try:
                    await log_channel.send(embed=embed, view=view)
                except discord.Forbidden:
                    print(f"Sem permissão no canal de log {log_channel_id} do servidor {guild.name}.")
            else:
                print(f"Canal de ID {log_channel_id} não encontrado no servidor {guild.name}.")