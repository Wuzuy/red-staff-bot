import discord
from discord.ext import commands
import asyncio

class ResetPermsConfirmationView(discord.ui.View):
    """View para confirmar a ação de resetar permissões."""
    def __init__(self, author: discord.User):
        super().__init__(timeout=60.0)
        self.author = author
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Apenas o autor do comando pode usar estes botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="✅ Confirmação recebida. Iniciando a redefinição de permissões...", embed=None, view=self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="❌ Ação cancelada.", embed=None, view=self)


class ResetPermsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="resetperms", aliases=["resetarperms"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def reset_perms(self, ctx: commands.Context):
        """Zera as permissões de todos os canais, sincronizando com a categoria."""

        view = ResetPermsConfirmationView(ctx.author)
        
        embed = discord.Embed(
            title="⚠️ Confirmação Necessária ⚠️",
            description=(
                "Você está prestes a **resetar as permissões de TODOS os canais** deste servidor "
                "para que herdem as permissões de suas respectivas categorias.\n\n"
                "Canais sem categoria não serão afetados.\n\n"
                "**Esta ação não pode ser desfeita.**"
            ),
            color=discord.Color.red()
        )
        
        msg = await ctx.send(embed=embed, view=view)

        await view.wait()

        if view.value is True:
            synced_channels = 0
            failed_channels = 0
            
            progress_embed = self.bot.create_embed("Redefinindo Permissões...", "Aguarde, sincronizando canais...")
            await msg.edit(embed=progress_embed, view=None)

            for channel in ctx.guild.channels:
                if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)) and channel.category is not None:
                    try:
                        await channel.edit(sync_permissions=True, reason=f"Redefinição de permissões por {ctx.author}")
                        synced_channels += 1
                        await asyncio.sleep(0.3) # Pequeno delay para evitar rate limit
                    except discord.Forbidden:
                        failed_channels += 1
                    except Exception as e:
                        failed_channels += 1
                        print(f"Erro ao resetar o canal {channel.id} no servidor {ctx.guild.id}: {e}")
            
            result_embed = self.bot.create_embed("Operação Concluída!", f"**{synced_channels}** canais sincronizados com sucesso.\n**{failed_channels}** canais falharam (verifique minhas permissões).")
            await msg.edit(embed=result_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ResetPermsCog(bot))