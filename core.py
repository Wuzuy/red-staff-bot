import discord
from discord.ext import commands
import os
import io
from datetime import datetime, timezone
import sqlite3

import config
from database.database_manager import initialize_database, DB_FILE

# Importa as novas classes de UI
from ui.base_view import BaseView
from ui import birthday_views, management_views, log_views


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
        
        # Anexa as classes de UI à instância do bot para fácil acesso
        self.BaseView = BaseView 
        self.BirthdayRegisterModal = birthday_views.BirthdayRegisterModal
        self.BirthdayRegisterView = birthday_views.BirthdayRegisterView
        self.AdminAddBirthdayModal = birthday_views.AdminAddBirthdayModal
        self.AdminChangeBirthdayModal = birthday_views.AdminChangeBirthdayModal
        self.AdminBirthdayManagementView = birthday_views.AdminBirthdayManagementView
        self.DmConfigView = management_views.DmConfigView
        self.ConfigPermView = management_views.ConfigPermView
        self.DmLogView = log_views.DmLogView


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
        self.add_view(self.BirthdayRegisterView())

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
                content += f"**__{month_name}__**\n"
                for bd in sorted(birthdays_by_month[month_num], key=lambda x: x['day']):
                    user = self.get_user(bd['user_id']) # Tenta pegar o usuário do cache
                    if user:
                        content += f"> <a:seta:EMOJI_SETA> `{bd['day']}` - <@{bd['user_id']}>\n"
                    else:
                        # Se o usuário não estiver no cache, apenas mostra o ID ou um placeholder
                        content += f"> <a:seta:EMOJI_SETA> `{bd['day']}` - Usuário desconhecido ({bd['user_id']})\n"
                content += "\n\n"  # Espaço entre os meses
        
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
                        title="Aniversários do Servidor <:firework:1431409168501182647>",
                        description=content,
                        color=0xffd700 # Gold color for birthdays
                    )
                    
                    # Adiciona o botão de registro de aniversário
                    # O autor da view persistente deve ser o bot para que ela funcione após reinícios
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