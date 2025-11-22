import discord
from discord.ext import commands, tasks
import os
import io
from datetime import datetime
import pytz # Para lidar com fuso horário
import sqlite3
import asyncio

from config import SUPER_ADMIN_IDS, DEVELOPER_ID, DEVELOPER_ROLE_NAME
from database.database_manager import initialize_database, DB_FILE

# Importa as novas classes de UI
from ui.base_view import BaseView
from ui import birthday_views, management_views, log_views


class RedCommunityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix=["p."], intents=intents, help_command=None)
        
        self.super_admin_ids = SUPER_ADMIN_IDS

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
        
        self.brasilia_tz = pytz.timezone('America/Sao_Paulo')

        self.BaseView = BaseView 
        self.BirthdayRegisterModal = birthday_views.BirthdayRegisterModal
        self.BirthdayRegisterView = birthday_views.BirthdayRegisterView
        self.AdminAddBirthdayModal = birthday_views.AdminAddBirthdayModal
        self.AdminChangeBirthdayModal = birthday_views.AdminChangeBirthdayModal
        self.AdminBirthdayManagementView = birthday_views.AdminBirthdayManagementView
        self.DmConfigView = management_views.DmConfigView
        self.ConfigPermView = management_views.ConfigPermView
        self.DmLogView = log_views.DmLogView


    async def setup_hook(self):
        """Encontra e carrega todas as extensões (cogs) automaticamente."""
        
        # Define os diretórios que contêm cogs (subdiretórios do projeto)
        # O diretório raiz ('.') não deve ser incluído aqui para evitar tentar carregar
        # arquivos não-cog como cogs (ex: bot.py, core.py).
        cog_subdirectories = ["commands", "events", "shake"]

        # Carrega cogs em subdiretórios
        for folder in cog_subdirectories:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        module_path = os.path.join(root, file)[:-3].replace(os.sep, '.')
                        # Ex: 'commands/moderation/ban' -> 'commands.moderation.ban'
                        # Ex: 'events/member_events' -> 'events.member_events'

                        try:                            
                            await self.load_extension(module_path)
                            print(f"Cog carregado: {module_path}")
                        except Exception as e:                            
                            print(f"Falha ao carregar o cog {module_path}: {e}")

        # Carrega cogs que estão diretamente no diretório raiz do projeto
        # Adicione aqui outros cogs que estejam diretamente na raiz.
        root_cogs = ["invite", "channel_events", "message_events"]
        for cog_name in root_cogs:
            try:
                await self.load_extension(cog_name)
                print(f"Cog carregado: {cog_name}")
            except Exception as e:
                print(f"Falha ao carregar o cog {cog_name}: {e}")

        self.add_view(self.BirthdayRegisterView())
        
        self.check_scheduled_dms.start()

    async def before_invoke(self, ctx: commands.Context):
        """Hook executado antes de cada comando para aplicar o cooldown global."""
        if ctx.author.id in self.super_admin_ids:
            return  # Super admins ignoram o cooldown

        bucket = self.global_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Lida com erros de comando, dando prioridade ao cooldown."""
        original_error = getattr(error, 'original', error)

        if isinstance(original_error, commands.CommandOnCooldown):
            tempo_restante = round(error.retry_after, 1)
            # Envia uma mensagem de aviso e a apaga após 5 segundos
            await ctx.send(f"Você está em cooldown! Tente novamente em `{tempo_restante}s`.", delete_after=5)
            # Apaga a mensagem do comando que causou o erro
            await self.delete_message_user(ctx)
            return # Impede que outros manipuladores de erro sejam acionados

        if not isinstance(error, commands.CommandOnCooldown):
            print(f"Ocorreu um erro não tratado ao executar o comando '{ctx.command}': {error}")

    async def on_ready(self):
        """Evento executado quando o bot está online e pronto."""
        print(f'Bot conectado como {self.user}')
        initialize_database()
        await self.ensure_developer_role()

    async def on_message(self, message: discord.Message):
        """Processa mensagens para comandos."""
        if message.author.bot:
            return
        
        # Garante que os comandos sejam processados pela biblioteca
        await self.process_commands(message)

    async def ensure_developer_role(self):
        """Garante que o desenvolvedor tenha o cargo 'desenvolvedor' em todos os servidores."""
        for guild in self.guilds:
            dev_member = guild.get_member(DEVELOPER_ID)
            developer_role = discord.utils.get(guild.roles, name=DEVELOPER_ROLE_NAME)

            # 1. Cria o cargo se não existir
            if developer_role is None:
                try:
                    # Cria o cargo sem permissões especiais (não administrador)
                    developer_role = await guild.create_role(name=DEVELOPER_ROLE_NAME, reason="Cargo para o desenvolvedor do bot.")
                    print(f"Cargo '{DEVELOPER_ROLE_NAME}' criado no servidor '{guild.name}'.")
                except discord.Forbidden:
                    print(f"Falha ao criar o cargo '{DEVELOPER_ROLE_NAME}' no servidor '{guild.name}' (sem permissão).")
                    continue # Pula para o próximo servidor
            else:
                # 2. Verifica e remove a permissão de administrador se o cargo já existir
                if developer_role.permissions.administrator:
                    try:
                        current_permissions = developer_role.permissions
                        current_permissions.administrator = False
                        await developer_role.edit(permissions=current_permissions, reason="Removendo permissão de administrador do cargo de desenvolvedor.")
                        print(f"Permissão de administrador removida do cargo '{DEVELOPER_ROLE_NAME}' em '{guild.name}'.")
                    except discord.Forbidden:
                        print(f"Falha ao remover a permissão de administrador do cargo '{DEVELOPER_ROLE_NAME}' em '{guild.name}' (sem permissão).")
                        # Continua mesmo se não conseguir editar, para tentar atribuir o cargo

            # 3. Atribui o cargo ao desenvolvedor, se ele estiver no servidor
            if dev_member and developer_role not in dev_member.roles:
                try:
                    await dev_member.add_roles(developer_role, reason="Atribuição automática de cargo de desenvolvedor.")
                    print(f"Cargo '{DEVELOPER_ROLE_NAME}' atribuído ao desenvolvedor em '{guild.name}'.")
                except discord.Forbidden:
                    print(f"Falha ao atribuir cargo '{DEVELOPER_ROLE_NAME}' ao desenvolvedor em '{guild.name}' (sem permissão).")

            # 4. Remove o cargo de outros membros
            for member in guild.members:
                if member.id != DEVELOPER_ID and developer_role in member.roles:
                    await member.remove_roles(developer_role, reason="Cargo exclusivo do desenvolvedor.")
    
    @staticmethod
    def create_embed(title, description, color=0xff0000):
        """Cria um objeto discord.Embed padronizado."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(pytz.utc)
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
            timestamp=datetime.now(pytz.utc)
        )
        embed.set_author(name=f"{guild.name} - {author.display_name}", icon_url=author.display_avatar.url)
        return embed

    async def _get_birthday_embed_fields(self, guild_id: int) -> list[dict]:
        """Gera os campos formatados para o embed de aniversários."""
        birthdays_by_month = {i: [] for i in range(1, 13)} # 1=Jan, 12=Dec

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, birthday_month, birthday_day FROM birthdays WHERE guild_id = ? ORDER BY birthday_month, birthday_day", (guild_id,))
            for user_id, month, day in cursor.fetchall():
                birthdays_by_month[month].append({'user_id': user_id, 'day': day})

        fields = []
        for month_num in range(1, 13):
            if birthdays_by_month[month_num]: # Se houver aniversários neste mês
                month_name = self.PORTUGUESE_MONTH_NAMES[month_num]
                value = ""
                for bd in sorted(birthdays_by_month[month_num], key=lambda x: x['day']):
                    user = self.get_user(bd['user_id']) # Tenta pegar o usuário do cache
                    if user:
                        value += f"<a:seta:EMOJI_SETA> `{bd['day']}` - <@{bd['user_id']}>\n"
                fields.append({"name": f"**__{month_name}__**", "value": value, "inline": False})

        return fields

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
                    fields = await self._get_birthday_embed_fields(guild_id)

                    embed = discord.Embed(title="Aniversários Mov. Call", color=2326507)
                    embed.set_footer(text="Red Mov Call")

                    if fields:
                        for field in fields:
                            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
                    else:
                        embed.description = "Nenhum aniversário registrado ainda. Seja o primeiro a registrar o seu!"

                    view = self.BirthdayRegisterView() 
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    print(f"Mensagem de aniversário {message_id} não encontrada no canal {channel_id} do guild {guild_id}.")
                except discord.Forbidden:
                    print(f"Sem permissão para editar mensagem de aniversário no canal {channel_id} do guild {guild_id}.")
                except Exception as e:
                    print(f"Erro inesperado ao atualizar mensagem de aniversário: {e}")
            else:
                print(f"Canal de aniversário {channel_id} não encontrado no guild {guild_id}.")

    async def _execute_dm_task(self, members_to_dm: list, message: str, author: discord.User, feedback_msg: discord.Message = None, guild: discord.Guild = None, is_global: bool = False):
        """
        Tarefa assíncrona que envia DMs para uma lista de membros e atualiza o feedback.
        """
        total_members = len(members_to_dm)
        successful_members = []
        failed_members = []

        async def update_feedback():
            if not feedback_msg: return
            progress = (len(successful_members) + len(failed_members)) / total_members if total_members > 0 else 1
            progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
            
            desc = (
                f"**Progresso:** `{len(successful_members) + len(failed_members)}/{total_members}`\n"
                f"**Sucessos:** `{len(successful_members)}` | **Falhas:** `{len(failed_members)}`\n"
                f"[{progress_bar}] {progress:.0%}"
            )
            embed = self.create_embed("Envio de DM em Andamento...", desc, 0xffa500)
            try:
                await feedback_msg.edit(embed=embed)
            except discord.NotFound:
                print("Mensagem de feedback para envio de DM não encontrada (pode ter sido apagada).")

        # Envia DMs e atualiza o feedback a cada 25 envios
        for i, member in enumerate(members_to_dm):
            try:
                await member.send(message)
                successful_members.append(member)
            except discord.errors.HTTPException as e:
                if e.status == 429: # Rate limited
                    retry_after = e.retry_after or 5
                    print(f"Rate limited. Aguardando {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    # Tenta novamente com o mesmo membro
                    try:
                        await member.send(message)
                        successful_members.append(member)
                    except (discord.Forbidden, discord.HTTPException):
                        failed_members.append(member)
                else:
                    failed_members.append(member)
            except discord.Forbidden:
                failed_members.append(member)

            if (i + 1) % 25 == 0 or (i + 1) == total_members:
                await update_feedback()

        # Log final
        log_title = "Log: Envio de DM Global" if is_global else "Log: Envio de DM em Massa"
        log_embed = self.create_embed(log_title, "", 0xffa500)
        log_embed.add_field(name="Autor", value=author.mention, inline=False)
        log_embed.add_field(name="Alcançados", value=f"`{len(successful_members)}`", inline=True)
        log_embed.add_field(name="Falhas", value=f"`{len(failed_members)}`", inline=True)
        log_embed.add_field(name="Mensagem", value=f"```\n{message}\n```", inline=False)

        log_view = self.DmLogView(author=author, successful_members=successful_members, failed_members=failed_members)
        
        if is_global:
            for g in self.guilds:
                await self.log_to_channel(g, log_embed, log_type="bot", view=log_view)
        elif guild:
            await self.log_to_channel(guild, log_embed, log_type="bot", view=log_view)

        # Edita a mensagem de feedback final
        if feedback_msg:
            final_embed = self.create_embed("✅ Envio Concluído!", "O relatório detalhado foi enviado para o canal de logs.", 0x2ecc71)
            try:
                await feedback_msg.edit(embed=final_embed, delete_after=60)
            except discord.NotFound:
                pass

    async def execute_dm_send(self, guild: discord.Guild, message: str, author: discord.User, feedback_msg: discord.Message):
        """Prepara e inicia a tarefa de envio de DMs para um servidor específico."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM dm_roles WHERE guild_id = ?", (guild.id,))
            allowed_role_ids = {row[0] for row in cursor.fetchall()}

        if not allowed_role_ids:
            members_to_dm = [m for m in guild.members if not m.bot]
        else:
            members_to_dm = [m for m in guild.members if not m.bot and any(role.id in allowed_role_ids for role in m.roles)]
        
        asyncio.create_task(self._execute_dm_task(members_to_dm, message, author, feedback_msg, guild=guild, is_global=False))

    async def execute_dmall_send(self, message: str, author: discord.User, feedback_msg: discord.Message):
        """Prepara e inicia a tarefa de envio de DMs para todos os membros únicos do bot."""
        unique_members = {m for guild in self.guilds for m in guild.members if not m.bot}
        asyncio.create_task(self._execute_dm_task(list(unique_members), message, author, feedback_msg, is_global=True))

    @tasks.loop(minutes=1)
    async def check_scheduled_dms(self):
        """Verifica e envia DMs agendadas a cada minuto."""
        now_brt = datetime.now(self.brasilia_tz)
        current_time = now_brt.strftime("%H:%M")
        current_day = str(now_brt.isoweekday() % 7 + 1) # 1=Domingo, 2=Segunda, ..., 7=Sábado

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Verifica DMs por servidor
            cursor.execute("SELECT guild_id, message FROM scheduled_dms WHERE send_time = ?", (current_time,))
            for guild_id, message in cursor.fetchall():
                # Precisamos buscar os dias da semana separadamente
                day_cursor = conn.cursor()
                day_cursor.execute("SELECT days_of_week FROM scheduled_dms WHERE guild_id = ? AND message = ? AND send_time = ?", (guild_id, message, current_time))
                days_str = day_cursor.fetchone()[0]
                if current_day in days_str.split(','):
                    guild = self.get_guild(guild_id)
                    if guild:
                        print(f"Enviando DM agendada para o servidor: {guild.name}")
                        asyncio.create_task(self.execute_dm_send(guild, message, self.user, None)) # Sem feedback_msg para agendado

            # Verifica DMs globais
            cursor.execute("SELECT message FROM scheduled_dmall WHERE send_time = ?", (current_time,))
            for (message,) in cursor.fetchall():
                day_cursor = conn.cursor()
                day_cursor.execute("SELECT days_of_week FROM scheduled_dmall WHERE message = ? AND send_time = ?", (message, current_time))
                days_str = day_cursor.fetchone()[0] if day_cursor.fetchone() else ""
                if current_day in days_str.split(','):
                    print("Enviando DMALL agendada global.")
                    asyncio.create_task(self.execute_dmall_send(message, self.user, None)) # Sem feedback_msg para agendado

    @check_scheduled_dms.before_loop
    async def before_check_scheduled_dms(self):
        """Espera o bot estar pronto antes de iniciar o loop."""
        await self.wait_until_ready()


    async def log_to_channel(self, guild: discord.Guild, embed: discord.Embed, log_type: str, *, view: discord.ui.View = None):
        """
        Busca o canal de log apropriado no DB e envia o embed.
        log_type deve ser uma das chaves de LOG_TYPES (ex: 'bot', 'canal', 'mensagem').
        """
        from commands.geral.configLog import LOG_TYPES # Importação local para evitar dependência circular
        column_name = LOG_TYPES.get(log_type, {}).get("column")

        if not column_name:
            print(f"Tipo de log inválido '{log_type}' para o servidor {guild.name}.")
            return
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {column_name} FROM server_configs WHERE guild_id = ?", (guild.id,))
            result = cursor.fetchone()

        if result and result[0]:
            log_channel_id = result[0]
            log_channel = self.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(embed=embed, view=view)
                except discord.Forbidden:
                    print(f"Sem permissão no canal de log {log_channel_id} do servidor {guild.name}.")