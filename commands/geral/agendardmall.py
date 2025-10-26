import discord
from discord.ext import commands
import sqlite3
import re
from ui.base_view import BaseView
from utils.checks import is_super_admin
from database.database_manager import DB_FILE

# O Modal é quase idêntico, mas salva em outra tabela
class ScheduleDMAllModal(discord.ui.Modal):
    def __init__(self, author_id: int):
        super().__init__(title="Agendar Nova Mensagem Global")
        self.author_id = author_id

        self.time_input = discord.ui.TextInput(label="Horário (HH:MM)", placeholder="Ex: 18:00", min_length=5, max_length=5)
        self.days_input = discord.ui.TextInput(label="Dias da Semana (1-7, separados por vírgula)", placeholder="1,2,3,4,5,6,7 (Todos os dias)", style=discord.TextStyle.short)
        self.message_input = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.long, placeholder="Sua mensagem global aqui...")
        
        self.add_item(self.time_input)
        self.add_item(self.days_input)
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value
        days_str = self.days_input.value
        message = self.message_input.value

        if not re.match(r"^\d{2}:\d{2}$", time_str):
            await interaction.response.send_message("Formato de hora inválido. Use HH:MM.", ephemeral=True)
            return
        
        try:
            days = sorted([str(int(d.strip())) for d in days_str.split(',') if 1 <= int(d.strip()) <= 7])
            if not days: raise ValueError
            days_db_str = ",".join(days)
        except (ValueError, IndexError):
            await interaction.response.send_message("Formato de dias inválido. Use números de 1 a 7 separados por vírgula.", ephemeral=True)
            return

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scheduled_dmall (message, send_time, days_of_week, created_by) VALUES (?, ?, ?, ?)",
                (message, time_str, days_db_str, self.author_id)
            )
            conn.commit()

        await interaction.response.send_message("✅ Agendamento global criado com sucesso!", ephemeral=True)
        await self.view.update_message(interaction, is_response=True)

class EditScheduleDMAllModal(discord.ui.Modal):
    def __init__(self, schedule_id: int, current_time: str, current_days: str, current_message: str):
        super().__init__(title=f"Editar Agendamento Global ID: {schedule_id}")
        self.schedule_id = schedule_id

        self.time_input = discord.ui.TextInput(label="Horário (HH:MM)", default=current_time, min_length=5, max_length=5)
        self.days_input = discord.ui.TextInput(label="Dias da Semana (1-7, separados por vírgula)", default=current_days, style=discord.TextStyle.short)
        self.message_input = discord.ui.TextInput(label="Mensagem", default=current_message, style=discord.TextStyle.long)

        self.add_item(self.time_input)
        self.add_item(self.days_input)
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value
        days_str = self.days_input.value
        message = self.message_input.value

        if not re.match(r"^\d{2}:\d{2}$", time_str):
            await interaction.response.send_message("Formato de hora inválido. Use HH:MM.", ephemeral=True)
            return

        try:
            days = sorted([str(int(d.strip())) for d in days_str.split(',') if 1 <= int(d.strip()) <= 7])
            if not days: raise ValueError
            days_db_str = ",".join(days)
        except (ValueError, IndexError):
            await interaction.response.send_message("Formato de dias inválido. Use números de 1 a 7 separados por vírgula.", ephemeral=True)
            return

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scheduled_dmall SET message = ?, send_time = ?, days_of_week = ? WHERE id = ?",
                (message, time_str, days_db_str, self.schedule_id)
            )
            conn.commit()

        await interaction.response.send_message("✅ Agendamento global atualizado com sucesso!", ephemeral=True)
        await self.view.update_message(interaction, is_response=True)

# A View também é similar
class ScheduleDMAllView(BaseView):
    def __init__(self, author: discord.User, bot_instance):
        super().__init__(author=author, timeout=900.0)
        self.bot_instance = bot_instance

    async def generate_embed(self) -> discord.Embed:
        embed = self.bot_instance.create_user_embed(self.author, self.author.mutual_guilds[0] if self.author.mutual_guilds else self.bot_instance.guilds[0], "Gerencie as mensagens automáticas globais.", title="Painel de Agendamento de DM All")
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, days_of_week, message FROM scheduled_dmall ORDER BY send_time")
            schedules = cursor.fetchall()

        if not schedules:
            embed.description += "\n\nNenhum agendamento global encontrado."
        else:
            day_map = {"1": "Dom", "2": "Seg", "3": "Ter", "4": "Qua", "5": "Qui", "6": "Sex", "7": "Sáb"}
            for schedule_id, send_time, days_of_week, message in schedules:
                days_formatted = ", ".join([day_map.get(d, "?") for d in days_of_week.split(',')])
                msg_preview = (message[:70] + '...') if len(message) > 70 else message
                embed.add_field(
                    name=f"ID: {schedule_id} | Horário: {send_time} | Dias: {days_formatted}",
                    value=f"```{msg_preview}```",
                    inline=False
                )
        return embed

    async def update_message(self, interaction: discord.Interaction, is_response: bool = False):
        embed = await self.generate_embed()
        if is_response:
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="<:adicionar:EMOJI_ADICIONAR>", row=0)
    async def add_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ScheduleDMAllModal(self.author.id)
        modal.view = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="<:editar:1431082844621930506>", row=0)
    async def edit_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, message FROM scheduled_dmall")
            schedules = cursor.fetchall()

        if not schedules:
            await interaction.response.send_message("Não há agendamentos para editar.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label=f"ID: {id} | {time} | " + (msg[:50] + '...' if len(msg) > 50 else msg), value=str(id))
            for id, time, msg in schedules
        ]
        select = discord.ui.Select(placeholder="Selecione o agendamento para editar...", options=options)

        async def select_callback(select_interaction: discord.Interaction):
            schedule_id_to_edit = int(select.values[0])
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT send_time, days_of_week, message FROM scheduled_dmall WHERE id = ?", (schedule_id_to_edit,))
                schedule_data = cursor.fetchone()
            
            self.remove_item(select)
            modal = EditScheduleDMAllModal(schedule_id_to_edit, schedule_data[0], schedule_data[1], schedule_data[2])
            modal.view = self
            await select_interaction.response.send_modal(modal)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="<:remover:EMOJI_REMOVER>", row=0)
    async def remove_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, message FROM scheduled_dmall")
            schedules = cursor.fetchall()

        if not schedules:
            await interaction.response.send_message("Não há agendamentos para remover.", ephemeral=True)
            return

        options = []
        for schedule_id, send_time, message in schedules:
            label = f"ID: {schedule_id} | {send_time} | " + (message[:50] + '...' if len(message) > 50 else message)
            options.append(discord.SelectOption(label=label, value=str(schedule_id)))

        select = discord.ui.Select(placeholder="Selecione o agendamento para remover...", options=options)

        async def select_callback(select_interaction: discord.Interaction):
            schedule_id_to_remove = select.values[0]
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scheduled_dmall WHERE id = ?", (schedule_id_to_remove,))
                conn.commit()
            
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

class AgendarDMAll(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="agendardmall")
    @commands.check(is_super_admin)
    async def agendardmall(self, ctx: commands.Context):
        """Abre o painel para gerenciar DMs agendadas globais."""
        await self.client.delete_message_user(ctx)
        view = ScheduleDMAllView(author=ctx.author, bot_instance=self.client)
        embed = await view.generate_embed()
        await ctx.send(embed=embed, view=view, delete_after=900)

    @agendardmall.error
    async def agendardmall_error(self, ctx: commands.Context, error):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{ctx.author.mention}, apenas Super Admins podem usar este comando.", delete_after=10)
        else:
            print(f"Erro em r.agendardmall: {error}")

async def setup(client: commands.Bot) -> None:
    await client.add_cog(AgendarDMAll(client))