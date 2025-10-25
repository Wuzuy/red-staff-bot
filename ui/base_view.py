import discord

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
