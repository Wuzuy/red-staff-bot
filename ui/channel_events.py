import discord
from discord.ext import commands

class ChannelEvents(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self.client.create_embed("Log: Canal Criado", "", 0x2ecc71)
        embed.add_field(name="Canal", value=channel.mention, inline=False)
        embed.add_field(name="Nome", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self.client.create_embed("Log: Canal Deletado", "", 0xe74c3c)
        embed.add_field(name="Nome", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
        await self.client.log_to_channel(channel.guild, embed, log_type="canal")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name != after.name:
            embed = self.client.create_embed("Log: Canal Renomeado", "", 0xf1c40f)
            embed.add_field(name="Canal", value=after.mention, inline=False)
            embed.add_field(name="Nome Antigo", value=f"`{before.name}`", inline=True)
            embed.add_field(name="Nome Novo", value=f"`{after.name}`", inline=True)
            await self.client.log_to_channel(after.guild, embed, log_type="canal")

async def setup(client: commands.Bot):
    await client.add_cog(ChannelEvents(client))