import discord
from discord.ext import commands
from ui.base_view import BaseView
from utils.checks import has_admin_role, is_call_server, is_chat_server, is_super_admin

def get_command_checks(command):
    """Função auxiliar para obter todos os checks de um comando, incluindo os de seus pais."""
    checks = set(command.checks)
    if command.parent:
        checks.update(get_command_checks(command.parent))
    return checks

class Help(commands.Cog):
    """
    Cog para o comando de ajuda personalizado.
    """
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        """Mostra uma lista de comandos disponíveis neste servidor."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        embed = self.client.create_user_embed(
            ctx.author,
            ctx.guild,
            "Selecione uma categoria abaixo para ver os comandos correspondentes.",
            title="Painel de Ajuda"
        )
        view = HelpView(author=ctx.author, bot_instance=self.client, original_ctx=ctx)
        await ctx.send(embed=embed, view=view, delete_after=300)

class HelpView(BaseView):
    def __init__(self, author: discord.User, bot_instance: commands.Bot, original_ctx: commands.Context):
        super().__init__(author=author, timeout=300.0)
        self.bot_instance = bot_instance
        self.original_ctx = original_ctx
        self.add_item(self.HelpSelect())

    class HelpSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Comandos Utilitários", value="util", description="Comandos úteis para todos."),
                discord.SelectOption(label="Comandos de Setor", value="setor", description="Comandos gerais para membros."),
                discord.SelectOption(label="Comandos de Admin", value="admin", description="Comandos para administradores do servidor."),
                discord.SelectOption(label="Comandos Super Admin", value="super_admin", description="Comandos para donos do bot.")
            ]
            super().__init__(placeholder="Escolha uma categoria de comandos...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            category = self.values[0]
            view: 'HelpView' = self.view
            
            title = ""
            description = ""
            filtered_commands = []

            all_commands = sorted(view.bot_instance.commands, key=lambda c: c.name)

            if category == "util":
                title = "Comandos Utilitários"
                description = "Comandos úteis disponíveis para todos os membros."

                for command in all_commands:
                    if command.hidden or command.name == "help": continue
                    
                    command_checks = get_command_checks(command)
                    # Adiciona comandos que não têm checks de permissão específicos
                    if not any(check in [has_admin_role, is_super_admin] for check in command_checks) and \
                       not any(getattr(check, 'is_sector_check', False) for check in command_checks):
                        filtered_commands.append(command)

            elif category == "setor":
                title = "Comandos de Setor"
                description = "Estes são os comandos específicos para este tipo de servidor."

                for command in all_commands:
                    if command.hidden or command.name == "help": continue
                    try:
                        command_checks = get_command_checks(command)
                        # Verifica se algum dos checks do comando tem o nosso atributo customizado
                        if any(getattr(check, 'is_sector_check', False) for check in command_checks):
                            if await command.can_run(view.original_ctx):
                                filtered_commands.append(command)
                    except commands.CommandError:
                        continue
            
            elif category == "admin":
                title = "Comandos de Admin"
                description = "Comandos disponíveis para administradores do servidor."
                for command in all_commands:
                    if command.hidden or command.name == "help": continue
                    command_checks = get_command_checks(command)
                    is_sector_command = any(getattr(check, 'is_sector_check', False) for check in command_checks)
                    if has_admin_role in command_checks and not is_sector_command:
                        filtered_commands.append(command)

            elif category == "super_admin":
                title = "Comandos Super Admin"
                description = "Comandos restritos para a administração do bot."
                for command in all_commands:
                    if command.hidden or command.name == "help": continue
                    if is_super_admin in get_command_checks(command):
                        filtered_commands.append(command)

            new_embed = view.bot_instance.create_user_embed(interaction.user, interaction.guild, description, title=title)

            if not filtered_commands:
                new_embed.description += "\n\nNenhum comando encontrado nesta categoria."
            else:
                cogs_with_commands = {}
                for cmd in filtered_commands:
                    cog_name = cmd.cog_name or "Outros"
                    if cog_name not in cogs_with_commands: cogs_with_commands[cog_name] = []
                    cogs_with_commands[cog_name].append(cmd)

                for cog_name, command_list in sorted(cogs_with_commands.items()):
                    command_text = "\n".join(f"`r.{cmd.qualified_name}` - {cmd.help or 'Sem descrição.'}" for cmd in sorted(command_list, key=lambda c: c.qualified_name))
                    if command_text: new_embed.add_field(name=f"**{cog_name}**", value=command_text, inline=False)

            await interaction.response.edit_message(embed=new_embed)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Help(client))