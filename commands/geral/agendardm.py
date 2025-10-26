import discord
from discord.ext import commands
import sqlite3
import re
from ui.base_view import BaseView
from utils.checks import has_admin_role
from database.database_manager import DB_FILE

class ScheduleDMModal(discord.ui.Modal):
    def __init__(self, guild_id: int, author_id: int):
        super().__init__(title="Agendar Nova Mensagem")
        self.guild_id = guild_id
        self.author_id = author_id

        self.time_input = discord.ui.TextInput(label="Horário (HH:MM)", placeholder="Ex: 09:30", min_length=5, max_length=5)
        self.days_input = discord.ui.TextInput(label="Dias da Semana (1-7, separados por vírgula)", placeholder="1,3,5 (Dom, Ter, Qui)", style=discord.TextStyle.short)
        self.message_input = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.long, placeholder="Sua mensagem aqui...")
        
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
                "INSERT INTO scheduled_dms (guild_id, message, send_time, days_of_week, created_by) VALUES (?, ?, ?, ?, ?)",
                (self.guild_id, message, time_str, days_db_str, self.author_id)
            )
            conn.commit()

        await interaction.response.send_message("✅ Agendamento criado com sucesso!", ephemeral=True)
        # Atualiza a view original
        await self.view.update_message(interaction, is_response=True)

class EditScheduleDMModal(discord.ui.Modal):
    def __init__(self, schedule_id: int, current_time: str, current_days: str, current_message: str):
        super().__init__(title=f"Editar Agendamento ID: {schedule_id}")
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
                "UPDATE scheduled_dms SET message = ?, send_time = ?, days_of_week = ? WHERE id = ?",
                (message, time_str, days_db_str, self.schedule_id)
            )
            conn.commit()

        await interaction.response.send_message("✅ Agendamento atualizado com sucesso!", ephemeral=True)
        await self.view.update_message(interaction, is_response=True)

class ScheduleDMView(BaseView):
    def __init__(self, author: discord.User, bot_instance, guild: discord.Guild):
        super().__init__(author=author, timeout=900.0)
        self.bot_instance = bot_instance
        self.guild = guild

    async def generate_embed(self) -> discord.Embed:
        embed = self.bot_instance.create_user_embed(self.author, self.guild, "Gerencie as mensagens automáticas para este servidor.", title="Painel de Agendamento de DMs")
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, days_of_week, message FROM scheduled_dms WHERE guild_id = ? ORDER BY send_time", (self.guild.id,))
            schedules = cursor.fetchall()

        if not schedules:
            embed.description += "\n\nNenhum agendamento encontrado."
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
            # on_submit já enviou uma resposta, então usamos follow-up para editar a mensagem original
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Adicionar", style=discord.ButtonStyle.success, emoji="<:adicionar:EMOJI_ADICIONAR>", row=0)
    async def add_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ScheduleDMModal(self.guild.id, self.author.id)
        modal.view = self # Passa a referência da view para o modal
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.primary, emoji="<:editar:1431082844621930506>", row=0)
    async def edit_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, message FROM scheduled_dms WHERE guild_id = ?", (self.guild.id,))
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
                cursor.execute("SELECT send_time, days_of_week, message FROM scheduled_dms WHERE id = ?", (schedule_id_to_edit,))
                schedule_data = cursor.fetchone()
            
            self.remove_item(select) # Limpa o select da view
            modal = EditScheduleDMModal(schedule_id_to_edit, schedule_data[0], schedule_data[1], schedule_data[2])
            modal.view = self
            await select_interaction.response.send_modal(modal)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="<:remover:EMOJI_REMOVER>", row=0)
    async def remove_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, send_time, message FROM scheduled_dms WHERE guild_id = ?", (self.guild.id,))
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
                cursor.execute("DELETE FROM scheduled_dms WHERE id = ? AND guild_id = ?", (schedule_id_to_remove, self.guild.id))
                conn.commit()
            
            self.remove_item(select)
            await self.update_message(select_interaction)

        select.callback = select_callback
        self.add_item(select)
        await interaction.response.edit_message(view=self)

class AgendarDM(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="agendardm")
    @commands.check(has_admin_role)
    async def agendardm(self, ctx: commands.Context):
        """Abre o painel para gerenciar DMs agendadas."""
        await self.client.delete_message_user(ctx)
        view = ScheduleDMView(author=ctx.author, bot_instance=self.client, guild=ctx.guild)
        embed = await view.generate_embed()
        await ctx.send(embed=embed, view=view, delete_after=900)

    @agendardm.error
    async def agendardm_error(self, ctx: commands.Context, error):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{ctx.author.mention}, você não tem permissão para usar este comando.", delete_after=10)
        else:
            print(f"Erro em r.agendardm: {error}")

async def setup(client: commands.Bot) -> None:
    await client.add_cog(AgendarDM(client))