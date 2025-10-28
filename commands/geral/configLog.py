import discord
from discord.ext import commands
import sqlite3
from database.database_manager import DB_FILE
from utils.checks import has_admin_role
from ui.base_view import BaseView

LOG_TYPES = {
    "bot": {"name": "Log do Bot", "column": "log_bot_channel_id", "description": "Logs de comandos e ações do bot."},
    "canal": {"name": "Log de Canais", "column": "log_channel_channel_id", "description": "Criação, exclusão e edição de canais."},
    "mensagem": {"name": "Log de Mensagens", "column": "log_message_channel_id", "description": "Mensagens editadas e apagadas."},
    "cargos": {"name": "Log de Cargos", "column": "log_role_channel_id", "description": "Criação, exclusão e edição de cargos."},
    "entrada": {"name": "Log de Entrada", "column": "log_join_channel_id", "description": "Registra quando um membro entra no servidor."},
    "saida": {"name": "Log de Saída", "column": "log_leave_channel_id", "description": "Registra quando um membro sai do servidor."},
    "moderacao": {"name": "Log de Moderação", "column": "log_moderation_channel_id", "description": "Logs de ban, kick, mute, etc."}
}

class ConfigLogView(BaseView):
    def __init__(self, author: discord.User, bot_instance, guild: discord.Guild):
        super().__init__(author=author, timeout=900.0)
        self.bot_instance = bot_instance
        self.guild = guild
        self.add_item(self.LogTypeSelect())

    async def generate_embed(self) -> discord.Embed:
        embed = self.bot_instance.create_user_embed(self.author, self.guild, "Configure os canais para cada tipo de log.", title="Painel de Configuração de Logs")
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM server_configs WHERE guild_id = ?", (self.guild.id,))
            config = cursor.fetchone()
            # Mapeia nome da coluna para valor
            config_dict = {desc[0]: val for desc, val in zip(cursor.description, config)} if config else {}

        for key, log_info in LOG_TYPES.items():
            channel_id = config_dict.get(log_info["column"])
            channel = self.guild.get_channel(channel_id) if channel_id else None
            value = channel.mention if channel else "`Não definido`"
            embed.add_field(name=f"**{log_info['name']}** (`{key}`)", value=value, inline=True)
        
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    class LogTypeSelect(discord.ui.Select):
        def __init__(self):
            options = [discord.SelectOption(label=info["name"], value=key, description=info["description"]) for key, info in LOG_TYPES.items()]
            super().__init__(placeholder="Selecione o tipo de log para configurar...", options=options)

        async def callback(self, interaction: discord.Interaction):
            view: 'ConfigLogView' = self.view
            view.add_item(view.ChannelSelect(self.values[0]))
            await interaction.response.edit_message(view=view)

    class ChannelSelect(discord.ui.ChannelSelect):
        def __init__(self, log_type: str):
            self.log_type = log_type
            super().__init__(placeholder=f"Selecione o canal para '{LOG_TYPES[log_type]['name']}'...", channel_types=[discord.ChannelType.text])

        async def callback(self, interaction: discord.Interaction):
            view: 'ConfigLogView' = self.view
            channel = self.values[0]
            column_name = LOG_TYPES[self.log_type]["column"]

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                # Garante que a linha para o guild exista
                cursor.execute("INSERT OR IGNORE INTO server_configs (guild_id) VALUES (?)", (view.guild.id,))
                # Atualiza a coluna específica
                cursor.execute(f"UPDATE server_configs SET {column_name} = ? WHERE guild_id = ?", (channel.id, view.guild.id))
                conn.commit()
            
            # Remove os menus de seleção para limpar a view e recria o inicial
            view.clear_items()
            view.add_item(view.LogTypeSelect())
            await view.update_message(interaction)

class ConfigLog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="configlog", help="Abre o painel para configurar os canais de log.")
    @commands.check(has_admin_role)
    async def configlog(self, ctx: commands.Context):
        """Abre um painel interativo para configurar os canais de log."""
        await self.client.delete_message_user(ctx)
        view = ConfigLogView(author=ctx.author, bot_instance=self.client, guild=ctx.guild)
        embed = await view.generate_embed()
        await ctx.send(embed=embed, view=view, delete_after=900)

    @configlog.error
    async def configlog_error(self, ctx: commands.Context, error):
        """Trata erros de sintaxe e permissão para o configlog."""
        await self.client.delete_message_user(ctx)
        
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando.\n"
                f"Apenas administradores ou cargos configurados podem usar.",
                delete_after=10
            )
        else:
            print(f"Erro em r.configlog: {error}")
            raise error

async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConfigLog(client))
