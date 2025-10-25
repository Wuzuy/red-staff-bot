import discord
from discord.ext import commands


class Help(commands.Cog):
    """
    Cog para o comando de ajuda personalizado.
    """
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        """Mostra uma lista de comandos disponíveis neste servidor."""
        await self.client.delete_message_user(ctx)

        embed = self.client.create_user_embed(
            ctx.author,
            ctx.guild,
            "Aqui estão os comandos que você pode usar neste servidor:",
            title="Painel de Ajuda"
        )

        # Dicionário para agrupar comandos por categoria (nome do cog)
        cogs_with_commands = {}

        for command in self.client.commands:
            # Ignora comandos ocultos e o próprio comando de ajuda
            if command.hidden or command.name == "help":
                continue

            try:
                # Verifica se o comando pode ser executado no contexto atual
                can_run = await command.can_run(ctx)
                if can_run:
                    cog_name = command.cog_name or "Outros"
                    if cog_name not in cogs_with_commands:
                        cogs_with_commands[cog_name] = []
                    cogs_with_commands[cog_name].append(command)
            except commands.CommandError:
                # Se a verificação gerar um erro (ex: CheckFailure), o comando não pode ser executado
                continue

        for cog_name, command_list in sorted(cogs_with_commands.items()):
            # Formata a lista de comandos para a categoria
            command_text = "\n".join(f"`r.{cmd.name}` - {cmd.help or 'Sem descrição.'}" for cmd in sorted(command_list, key=lambda c: c.name))
            if command_text:
                embed.add_field(name=f"**{cog_name}**", value=command_text, inline=False)

        await ctx.send(embed=embed, delete_after=300) # A mensagem de ajuda some após 5 minutos

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Help(client))