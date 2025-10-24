import discord
from discord.ext import commands
import os
import io
import sqlite3
from datetime import datetime, timezone

import config
from database.database_manager import initialize_database, DB_FILE
import discord.ui


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
        
        self.PORTUGUESE_MONTH_NAMES = {
            1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
            5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
            9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
        }


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

        # Adiciona as views persistentes para que funcionem após o reinício do bot
        self.add_view(self.BirthdayRegisterView(author=self.user))

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

    # --- NOVAS FUNÇÕES PARA ANIVERSÁRIOS ---
    async def _get_birthday_embed_content(self, guild_id: int) -> str:
        """Gera o conteúdo formatado para o embed de aniversários."""
        birthdays_by_month = {i: [] for i in range(1, 13)} # 1=Jan, 12=Dec

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, birthday_month, birthday_day FROM birthdays WHERE guild_id = ? ORDER BY birthday_month, birthday_day", (guild_id,))
            for user_id, month, day in cursor.fetchall():
                birthdays_by_month[month].append({'user_id': user_id, 'day': day})
        
        content = ""
        for month_num in range(1, 13):
            if birthdays_by_month[month_num]: # Se houver aniversários neste mês
                month_name = self.PORTUGUESE_MONTH_NAMES[month_num]
                content += f"**{month_name}:**\n"
                for bd in sorted(birthdays_by_month[month_num], key=lambda x: x['day']):
                    user = self.get_user(bd['user_id']) # Tenta pegar o usuário do cache
                    if user:
                        content += f"> {bd['day']} - <@{bd['user_id']}>\n"
                    else:
                        # Se o usuário não estiver no cache, apenas mostra o ID ou um placeholder
                        content += f"> {bd['day']} - Usuário desconhecido ({bd['user_id']})\n"
                content += "\n" # Espaço entre os meses
        
        if not content:
            content = "Nenhum aniversário registrado ainda. Seja o primeiro a registrar o seu!"
        
        return content

    async def _update_birthday_message(self, guild_id: int):
        """Busca o canal e a mensagem de aniversário e a atualiza."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT birthday_channel_id, birthday_message_id FROM server_configs WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
        
        if result and result[0] and result[1]:
            channel_id, message_id = result
            channel = self.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    content = await self._get_birthday_embed_content(guild_id)
                    
                    embed = self.create_embed(
                        title="🎉 Aniversários do Servidor 🎉",
                        description=content,
                        color=0xffd700 # Gold color for birthdays
                    )
                    
                    # Adiciona o botão de registro de aniversário
                    # O autor da view persistente deve ser o bot para que ela funcione após reinícios
                    view = self.BirthdayRegisterView(author=self.user, guild=self.get_guild(guild_id), bot_instance=self) 
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    print(f"Mensagem de aniversário {message_id} não encontrada no canal {channel_id} do guild {guild_id}.")
                except discord.Forbidden:
                    print(f"Sem permissão para editar mensagem de aniversário no canal {channel_id} do guild {guild_id}.")
                except Exception as e:
                    print(f"Erro inesperado ao atualizar mensagem de aniversário: {e}")
            else:
                print(f"Canal de aniversário {channel_id} não encontrado no guild {guild_id}.")
        else:
            print(f"Nenhuma mensagem de aniversário configurada para o guild {guild_id}.")

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

    # --- NOVAS VIEWS E MODALS PARA ANIVERSÁRIOS ---

    class BirthdayRegisterModal(discord.ui.Modal, title="Registrar seu Aniversário"):
        def __init__(self, bot_instance: 'RedCommunityBot', guild: discord.Guild):
            super().__init__()
            self.bot_instance = bot_instance
            self.guild = guild

        day_input = discord.ui.TextInput(
            label="Dia do Aniversário (1-31)",
            placeholder="Ex: 15",
            min_length=1,
            max_length=2,
            required=True
        )
        month_input = discord.ui.TextInput(
            label="Mês do Aniversário (1-12)",
            placeholder="Ex: 7 (para Julho)",
            min_length=1,
            max_length=2,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                day = int(self.day_input.value)
                month = int(self.month_input.value)

                if not (1 <= day <= 31 and 1 <= month <= 12):
                    await interaction.response.send_message("Dia ou mês inválido. Por favor, insira valores entre 1-31 para o dia e 1-12 para o mês.", ephemeral=True)
                    return
                
                # Basic check for valid day in month (e.g., no Feb 30)
                try:
                    datetime(2000, month, day) # Use a leap year to allow Feb 29
                except ValueError:
                    await interaction.response.send_message(f"O dia {day} não é válido para o mês {month}. Por favor, verifique.", ephemeral=True)
                    return

                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    # Verifica se o usuário já tem um aniversário registrado
                    cursor.execute("SELECT * FROM birthdays WHERE guild_id = ? AND user_id = ?", (self.guild.id, interaction.user.id))
                    existing_birthday = cursor.fetchone()

                    if existing_birthday:
                        await interaction.response.send_message("Você já tem um aniversário registrado. Se precisar alterar, entre em contato com um administrador.", ephemeral=True)
                        return

                    cursor.execute("INSERT INTO birthdays (guild_id, user_id, birthday_month, birthday_day) VALUES (?, ?, ?, ?)",
                                   (self.guild.id, interaction.user.id, month, day))
                    conn.commit()
                
                # Log da ação
                log_description = (
                    f"**Ação:** Aniversário Registrado\n"
                    f"**Usuário:** {interaction.user.mention}\n"
                    f"**Data:** `{day}/{month}`"
                )
                log_embed = self.bot_instance.create_user_embed(
                    interaction.user, self.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0x2ecc71
                )
                await self.bot_instance.log_to_channel(self.guild, log_embed)

                await interaction.response.send_message("Seu aniversário foi registrado com sucesso! 🎉", ephemeral=True)
                await self.bot_instance._update_birthday_message(self.guild.id) # Atualiza o embed
            except ValueError:
                await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
            except Exception as e:
                print(f"Erro ao registrar aniversário: {e}")
                await interaction.response.send_message("Ocorreu um erro ao registrar seu aniversário. Tente novamente mais tarde.", ephemeral=True)

    class BirthdayRegisterView(discord.ui.View):
        def __init__(self, author: discord.User, guild: discord.Guild = None, bot_instance: 'RedCommunityBot' = None):
            super().__init__(timeout=None) # Persistente
            self.guild = guild 
            self.bot_instance = bot_instance # Pode ser None se a view for carregada de forma persistente

        async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
            print(f"Erro na BirthdayRegisterView: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Ocorreu um erro inesperado. Tente novamente mais tarde.", ephemeral=True)

        @discord.ui.button(label="Registrar Aniversário", style=discord.ButtonStyle.primary, emoji="🎂", custom_id="birthday_register_button")
        async def register_birthday_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Para views persistentes, guild e bot_instance podem ser None no __init__
            # Obtemos a guild e a instância do bot da interação
            self.guild = interaction.guild
            if self.bot_instance is None:
                self.bot_instance = interaction.client # interaction.client é a instância do bot
            modal = self.bot_instance.BirthdayRegisterModal(self.bot_instance, self.guild)
            await interaction.response.send_modal(modal)

    # --- ADMIN BIRTHDAY MANAGEMENT VIEWS ---

    class AdminAddBirthdayModal(discord.ui.Modal, title="Adicionar Aniversário (Admin)"):
        def __init__(self, bot_instance: 'RedCommunityBot', guild: discord.Guild):
            super().__init__()
            self.bot_instance = bot_instance
            self.guild = guild

        user_input = discord.ui.TextInput(
            label="ID ou Menção do Usuário",
            placeholder="Ex: 1234567890 ou @Usuário",
            required=True
        )
        day_input = discord.ui.TextInput(
            label="Dia do Aniversário (1-31)",
            placeholder="Ex: 15",
            min_length=1,
            max_length=2,
            required=True
        )
        month_input = discord.ui.TextInput(
            label="Mês do Aniversário (1-12)",
            placeholder="Ex: 7 (para Julho)",
            min_length=1,
            max_length=2,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_str = self.user_input.value.strip()
                user_id = None
                if user_str.isdigit():
                    user_id = int(user_str)
                elif user_str.startswith('<@') and user_str.endswith('>'):
                    user_id = int(user_str.strip('<@!>'))
                
                if not user_id:
                    await interaction.response.send_message("Formato de usuário inválido. Por favor, use o ID ou a menção.", ephemeral=True)
                    return
                
                target_user = self.bot_instance.get_user(user_id)
                if not target_user:
                    await interaction.response.send_message(f"Não consegui encontrar o usuário com ID {user_id}.", ephemeral=True)
                    return

                day = int(self.day_input.value)
                month = int(self.month_input.value)

                if not (1 <= day <= 31 and 1 <= month <= 12):
                    await interaction.response.send_message("Dia ou mês inválido. Por favor, insira valores entre 1-31 para o dia e 1-12 para o mês.", ephemeral=True)
                    return
                
                try:
                    datetime(2000, month, day)
                except ValueError:
                    await interaction.response.send_message(f"O dia {day} não é válido para o mês {month}. Por favor, verifique.", ephemeral=True)
                    return

                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO birthdays (guild_id, user_id, birthday_month, birthday_day) VALUES (?, ?, ?, ?)",
                                   (self.guild.id, user_id, month, day))
                    conn.commit()
                
                # Log da ação
                log_description = (
                    f"**Ação:** Aniversário Adicionado/Alterado (Admin)\n"
                    f"**Moderador:** {interaction.user.mention}\n"
                    f"**Alvo:** {target_user.mention}\n"
                    f"**Nova Data:** `{day}/{month}`"
                )
                log_embed = self.bot_instance.create_user_embed(
                    interaction.user, self.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0x00bfff
                )
                await self.bot_instance.log_to_channel(self.guild, log_embed)

                await interaction.response.send_message(f"Aniversário de {target_user.display_name} ({day}/{month}) adicionado/atualizado com sucesso! 🎉", ephemeral=True)
                await self.bot_instance._update_birthday_message(self.guild.id)
            except ValueError:
                await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
            except Exception as e:
                print(f"Erro ao adicionar aniversário (Admin): {e}")
                await interaction.response.send_message("Ocorreu um erro ao adicionar o aniversário. Tente novamente mais tarde.", ephemeral=True)

    class AdminChangeBirthdayModal(discord.ui.Modal, title="Alterar Aniversário (Admin)"):
        def __init__(self, bot_instance: 'RedCommunityBot', guild: discord.Guild, user_id: int, current_day: int, current_month: int):
            super().__init__()
            self.bot_instance = bot_instance
            self.guild = guild
            self.user_id = user_id

            self.day_input = discord.ui.TextInput(
                label="Novo Dia do Aniversário (1-31)",
                placeholder=f"Dia atual: {current_day}",
                min_length=1,
                max_length=2,
                default=str(current_day),
                required=True
            )
            self.month_input = discord.ui.TextInput(
                label="Novo Mês do Aniversário (1-12)",
                placeholder=f"Mês atual: {current_month}",
                min_length=1,
                max_length=2,
                default=str(current_month),
                required=True
            )
            self.add_item(self.day_input)
            self.add_item(self.month_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                day = int(self.day_input.value)
                month = int(self.month_input.value)

                if not (1 <= day <= 31 and 1 <= month <= 12):
                    await interaction.response.send_message("Dia ou mês inválido. Por favor, insira valores entre 1-31 para o dia e 1-12 para o mês.", ephemeral=True)
                    return
                
                try:
                    datetime(2000, month, day)
                except ValueError:
                    await interaction.response.send_message(f"O dia {day} não é válido para o mês {month}. Por favor, verifique.", ephemeral=True)
                    return

                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE birthdays SET birthday_month = ?, birthday_day = ? WHERE guild_id = ? AND user_id = ?",
                                   (month, day, self.guild.id, self.user_id))
                    conn.commit()
                
                # Log da ação
                target_user = self.bot_instance.get_user(self.user_id)
                log_description = (
                    f"**Ação:** Aniversário Alterado (Admin)\n"
                    f"**Moderador:** {interaction.user.mention}\n"
                    f"**Alvo:** {target_user.mention if target_user else f'ID: {self.user_id}'}\n"
                    f"**Nova Data:** `{day}/{month}`"
                )
                log_embed = self.bot_instance.create_user_embed(
                    interaction.user, self.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0xf1c40f
                )
                await self.bot_instance.log_to_channel(self.guild, log_embed)

                target_user = self.bot_instance.get_user(self.user_id)
                user_name = target_user.display_name if target_user else f"Usuário {self.user_id}"
                await interaction.response.send_message(f"Aniversário de {user_name} alterado para {day}/{month} com sucesso! 🎉", ephemeral=True)
                await self.bot_instance._update_birthday_message(self.guild.id)
            except ValueError:
                await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
            except Exception as e:
                print(f"Erro ao alterar aniversário (Admin): {e}")
                await interaction.response.send_message("Ocorreu um erro ao alterar o aniversário. Tente novamente mais tarde.", ephemeral=True)


    class AdminBirthdayManagementView(BaseView):
        def __init__(self, author: discord.User, guild: discord.Guild = None, bot_instance: 'RedCommunityBot' = None):
            super().__init__(author=author, timeout=900.0)
            self.guild = guild
            self.bot_instance = bot_instance

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            # Para views persistentes, guild e bot_instance podem ser None no __init__
            if self.guild is None: self.guild = interaction.guild
            if self.bot_instance is None: self.bot_instance = interaction.client
            return await super().interaction_check(interaction)

        @discord.ui.button(label="Adicionar Aniversário", style=discord.ButtonStyle.success, emoji="➕")
        async def add_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = self.bot_instance.AdminAddBirthdayModal(self.bot_instance, self.guild)
            await interaction.response.send_modal(modal)

        @discord.ui.button(label="Remover Aniversário", style=discord.ButtonStyle.danger, emoji="➖")
        async def remove_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, birthday_month, birthday_day FROM birthdays WHERE guild_id = ? ORDER BY birthday_month, birthday_day", (self.guild.id,))
                birthdays_data = cursor.fetchall()
            
            if not birthdays_data:
                await interaction.response.send_message("Não há aniversários registrados para remover.", ephemeral=True)
                return
            
            options = []
            for user_id, month, day in birthdays_data:
                user = self.bot_instance.get_user(user_id)
                user_name = user.display_name if user else f"Usuário {user_id}"
                options.append(discord.SelectOption(label=f"{user_name} ({day}/{month})", value=str(user_id)))
            
            select = discord.ui.Select(placeholder="Selecione o usuário para remover o aniversário...", min_values=1, max_values=len(options), options=options)

            async def select_callback(select_interaction: discord.Interaction):
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    for user_id_str in select.values:
                        user_id = int(user_id_str)
                        cursor.execute("DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?", (self.guild.id, user_id))
                        
                        # Log da ação para cada usuário removido
                        target_user = self.bot_instance.get_user(user_id)
                        log_description = (
                            f"**Ação:** Aniversário Removido (Admin)\n"
                            f"**Moderador:** {select_interaction.user.mention}\n"
                            f"**Alvo:** {target_user.mention if target_user else f'ID: {user_id}'}"
                        )
                        log_embed = self.bot_instance.create_user_embed(
                            select_interaction.user, self.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0xe74c3c
                        )
                        await self.bot_instance.log_to_channel(self.guild, log_embed)

                    conn.commit()

                await select_interaction.response.send_message("Aniversário(s) removido(s) com sucesso!", ephemeral=True)
                await self.bot_instance._update_birthday_message(self.guild.id)
                # Remove o select da view e atualiza a mensagem
                self.remove_item(select)
                await select_interaction.message.edit(view=self) # Edita a mensagem original do painel admin
            
            select.callback = select_callback
            self.add_item(select)
            await interaction.response.edit_message(view=self) # Atualiza a view para mostrar o select

        @discord.ui.button(label="Alterar Aniversário", style=discord.ButtonStyle.secondary, emoji="✏️")
        async def change_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, birthday_month, birthday_day FROM birthdays WHERE guild_id = ? ORDER BY birthday_month, birthday_day", (self.guild.id,))
                birthdays_data = cursor.fetchall()
            
            if not birthdays_data:
                await interaction.response.send_message("Não há aniversários registrados para alterar.", ephemeral=True)
                return
            
            options = []
            for user_id, month, day in birthdays_data:
                user = self.bot_instance.get_user(user_id)
                user_name = user.display_name if user else f"Usuário {user_id}"
                options.append(discord.SelectOption(label=f"{user_name} ({day}/{month})", value=f"{user_id},{day},{month}")) # Value: user_id,day,month
            
            select = discord.ui.Select(placeholder="Selecione o usuário para alterar o aniversário...", min_values=1, max_values=1, options=options)

            async def select_callback(select_interaction: discord.Interaction):
                selected_value = select.values[0]
                user_id_str, day_str, month_str = selected_value.split(',')
                user_id = int(user_id_str)
                current_day = int(day_str)
                current_month = int(month_str)

                modal = self.bot_instance.AdminChangeBirthdayModal(self.bot_instance, self.guild, user_id, current_day, current_month)
                await select_interaction.response.send_modal(modal)
                # Remove o select da view e atualiza a mensagem
                self.remove_item(select)
                await select_interaction.message.edit(view=self) # Edita a mensagem original do painel admin
            
            select.callback = select_callback
            self.add_item(select)
            await interaction.response.edit_message(view=self) # Atualiza a view para mostrar o select

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