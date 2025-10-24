import discord
from discord.ext import commands
import sqlite3
from utils.checks import is_call_server, has_admin_role
from database.database_manager import DB_FILE

class Birthday(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="birthday")
    @is_call_server() # Garante que o comando só pode ser usado em servidores de call
    @commands.check(has_admin_role) # Apenas admins podem configurar o painel de aniversário
    async def birthday(self, ctx: commands.Context):
        """
        Cria ou atualiza o painel de aniversários no canal atual.
        Apenas para servidores de call.
        """
        await self.client.delete_message_user(ctx)

        # Tenta buscar a mensagem existente
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT birthday_channel_id, birthday_message_id FROM server_configs WHERE guild_id = ?", (ctx.guild.id,))
            result = cursor.fetchone()
        
        content = await self.client._get_birthday_embed_content(ctx.guild.id)
        embed = self.client.create_embed(
            title="Aniversários do Servidor <:firework:1431409168501182647>",
            description=content,
            color=0xffd700 # Gold color for birthdays
        )
        view = self.client.BirthdayRegisterView(author=self.client.user, guild=ctx.guild, bot_instance=self.client) # Bot é o autor da view persistente

        if result and result[0] == ctx.channel.id and result[1]:
            # Mensagem já existe no canal atual, tenta editar
            try:
                message = await ctx.channel.fetch_message(result[1])
                await message.edit(embed=embed, view=view)
                await ctx.send("Painel de aniversários atualizado com sucesso!", delete_after=10)
            except (discord.NotFound, discord.Forbidden):
                # Mensagem não encontrada ou sem permissão, cria uma nova
                message = await ctx.send(embed=embed, view=view)
                await ctx.send("Painel de aniversários criado com sucesso!", delete_after=10)
        else:
            # Cria uma nova mensagem
            message = await ctx.send(embed=embed, view=view)
            await ctx.send("Painel de aniversários criado com sucesso!", delete_after=10)

        # Salva/atualiza o ID da mensagem e do canal no DB
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO server_configs (guild_id, birthday_channel_id, birthday_message_id) VALUES (?, ?, ?)",
                           (ctx.guild.id, ctx.channel.id, message.id))
            conn.commit()

    @birthday.error
    async def birthday_error(self, ctx: commands.Context, error):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                f"{ctx.author.mention}, você não tem permissão para usar este comando ou ele não pode ser usado neste servidor.",
                delete_after=10
            )
        else:
            print(f"Erro no comando r.birthday: {error}")
            await ctx.send(f"{ctx.author.mention}, ocorreu um erro ao executar o comando.", delete_after=10)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Birthday(client))