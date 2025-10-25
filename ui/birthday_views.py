import discord
import sqlite3
from datetime import datetime
from database.database_manager import DB_FILE
from .base_view import BaseView

# --- MODALS ---

class BirthdayRegisterModal(discord.ui.Modal, title="Registrar seu Aniversário"):
    def __init__(self, bot_instance, guild: discord.Guild):
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
            await self.bot_instance.log_to_channel(self.guild, log_embed, log_type="bot")

            await interaction.response.send_message("Seu aniversário foi registrado com sucesso! 🎉", ephemeral=True)
            await self.bot_instance._update_birthday_message(self.guild.id) # Atualiza o embed
        except ValueError:
            await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao registrar aniversário: {e}")
            await interaction.response.send_message("Ocorreu um erro ao registrar seu aniversário. Tente novamente mais tarde.", ephemeral=True)

class AdminAddBirthdayModal(discord.ui.Modal, title="Adicionar Aniversário (Admin)"):
    def __init__(self, bot_instance, guild: discord.Guild):
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
            await self.bot_instance.log_to_channel(self.guild, log_embed, log_type="bot")

            await interaction.response.send_message(f"Aniversário de {target_user.display_name} ({day}/{month}) adicionado/atualizado com sucesso! 🎉", ephemeral=True)
            await self.bot_instance._update_birthday_message(self.guild.id)
        except ValueError:
            await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao adicionar aniversário (Admin): {e}")
            await interaction.response.send_message("Ocorreu um erro ao adicionar o aniversário. Tente novamente mais tarde.", ephemeral=True)

class AdminChangeBirthdayModal(discord.ui.Modal, title="Alterar Aniversário (Admin)"):
    def __init__(self, bot_instance, guild: discord.Guild, user_id: int, current_day: int, current_month: int):
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
            await self.bot_instance.log_to_channel(self.guild, log_embed, log_type="bot")

            user_name = target_user.display_name if target_user else f"Usuário {self.user_id}"
            await interaction.response.send_message(f"Aniversário de {user_name} alterado para {day}/{month} com sucesso! 🎉", ephemeral=True)
            await self.bot_instance._update_birthday_message(self.guild.id)
        except ValueError:
            await interaction.response.send_message("Por favor, insira apenas números para o dia e o mês.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao alterar aniversário (Admin): {e}")
            await interaction.response.send_message("Ocorreu um erro ao alterar o aniversário. Tente novamente mais tarde.", ephemeral=True)

# --- VIEWS ---

class BirthdayRegisterView(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(f"Erro na BirthdayRegisterView: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Ocorreu um erro inesperado. Tente novamente mais tarde.", ephemeral=True)

    @discord.ui.button(label="Registrar Aniversário", style=discord.ButtonStyle.primary, emoji="🎂", custom_id="birthday_register_button")
    async def register_birthday_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        bot_instance = interaction.client
        modal = BirthdayRegisterModal(bot_instance, interaction.guild)
        await interaction.response.send_modal(modal)

class AdminBirthdayManagementView(BaseView):
    def __init__(self, author: discord.User, bot_instance, guild: discord.Guild):
        super().__init__(author=author, timeout=900.0)
        self.bot_instance = bot_instance
        self.guild = guild

    @discord.ui.button(label="Adicionar Aniversário", style=discord.ButtonStyle.success, emoji="➕")
    async def add_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AdminAddBirthdayModal(self.bot_instance, self.guild)
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
        
        select = discord.ui.Select(placeholder="Selecione o usuário para remover o aniversário...", min_values=1, max_values=min(25, len(options)), options=options)

        async def select_callback(select_interaction: discord.Interaction):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for user_id_str in select.values:
                    user_id = int(user_id_str)
                    cursor.execute("DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?", (self.guild.id, user_id))
                    
                    target_user = self.bot_instance.get_user(user_id)
                    log_description = (
                        f"**Ação:** Aniversário Removido (Admin)\n"
                        f"**Moderador:** {select_interaction.user.mention}\n"
                        f"**Alvo:** {target_user.mention if target_user else f'ID: {user_id}'}"
                    )
                    log_embed = self.bot_instance.create_user_embed(
                        select_interaction.user, self.guild, log_description, title="Log: Gerenciamento de Aniversários", color=0xe74c3c
                    )
                    await self.bot_instance.log_to_channel(self.guild, log_embed, log_type="bot")

                conn.commit()

            await select_interaction.response.send_message("Aniversário(s) removido(s) com sucesso!", ephemeral=True)
            await self.bot_instance._update_birthday_message(self.guild.id)
            self.remove_item(select)
            await select_interaction.message.edit(view=self)
        
        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

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
            options.append(discord.SelectOption(label=f"{user_name} ({day}/{month})", value=f"{user_id},{day},{month}"))
        
        select = discord.ui.Select(placeholder="Selecione o usuário para alterar o aniversário...", min_values=1, max_values=1, options=options)

        async def select_callback(select_interaction: discord.Interaction):
            selected_value = select.values[0]
            user_id_str, day_str, month_str = selected_value.split(',')
            user_id = int(user_id_str)
            current_day = int(day_str)
            current_month = int(month_str)

            modal = AdminChangeBirthdayModal(self.bot_instance, self.guild, user_id, current_day, current_month)
            await select_interaction.response.send_modal(modal)
            self.remove_item(select)
            await select_interaction.message.edit(view=self)
        
        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)