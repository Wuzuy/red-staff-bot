import discord
from discord.ext import commands

class MessageEvents(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        embed = self.client.create_embed("Log: Mensagem Apagada", "", 0xe74c3c)
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Canal", value=message.channel.mention, inline=False)
        if message.content:
            embed.add_field(name="Conteúdo", value=f"```\n{message.content[:1000]}\n```", inline=False)
        if message.attachments:
            embed.add_field(name="Anexos", value="\n".join([f.filename for f in message.attachments]), inline=False)
        
        await self.client.log_to_channel(message.guild, embed, log_type="mensagem")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content: return

        embed = self.client.create_embed("Log: Mensagem Editada", f"[Ir para a mensagem]({after.jump_url})", 0xf1c40f)
        embed.set_author(name=f"{before.author.name} ({before.author.id})", icon_url=before.author.display_avatar.url)
        embed.add_field(name="Canal", value=before.channel.mention, inline=False)
        if before.content:
            embed.add_field(name="Antes", value=f"```\n{before.content[:1000]}\n```", inline=False)
        if after.content:
            embed.add_field(name="Depois", value=f"```\n{after.content[:1000]}\n```", inline=False)

        await self.client.log_to_channel(before.guild, embed, log_type="mensagem")

async def setup(client: commands.Bot):
    await client.add_cog(MessageEvents(client))