import discord
from discord.ext import commands

class Text(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="text", help="Formata um texto para ser copiado facilmente.")
    async def text(self, ctx: commands.Context, *, content: str):
        """
        Recebe um texto e o envia de volta dentro de um bloco de código,
        facilitando a cópia de formatos complexos como emojis customizados.
        """
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if not content:
            await ctx.send(f"{ctx.author.mention}, você precisa fornecer um texto. Ex: `r.text :meu_emoji: #Olá a todos!`", delete_after=10)
            return

        # Envia o conteúdo formatado em um bloco de código
        await ctx.send(f"{ctx.author.mention}\n```{content}```")

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Text(client))