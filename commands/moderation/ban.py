import discord
from discord.ext import commands
from utils.checks import can_moderate

class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="ban")
    @commands.check(can_moderate)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Motivo não especificado."):
        """
        Bane um membro do servidor.
        É possível especificar um motivo.
        """
        await self.client.delete_message_user(ctx)

        if member == ctx.author:
            await ctx.send("Você não pode banir a si mesmo.", delete_after=10)
            return

        if member.id in self.client.super_admin_ids:
            await ctx.send("Você não pode banir um Super Admin.", delete_after=10)
            return

        if ctx.author.top_role <= member.top_role and ctx.guild.owner != ctx.author:
            await ctx.send("Você não pode banir um membro com cargo igual ou superior ao seu.", delete_after=10)
            return

        # Tenta enviar DM para o membro antes de banir
        try:
            dm_embed = self.client.create_embed(
                "Você foi banido!",
                f"Você foi banido do servidor **{ctx.guild.name}**.\n\n**Motivo:** {reason}",
                color=0xff0000
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            # Não consegue enviar DM, mas continua com o banimento
            pass
        except Exception as e:
            print(f"Erro ao tentar enviar DM de banimento para {member.name}: {e}")

        # Bane o membro
        try:
            await member.ban(reason=f"Banido por {ctx.author.name}. Motivo: {reason}")
            
            # Mensagem de confirmação no canal
            await ctx.send(f"✅ {member.mention} foi banido com sucesso.", delete_after=10)

            # Log do banimento
            log_description = (
                f"**Ação:** Banimento\n"
                f"**Alvo:** {member.mention} (`{member.id}`)\n"
                f"**Moderador:** {ctx.author.mention}\n"
                f"**Motivo:** {reason}"
            )
            log_embed = self.client.create_user_embed(
                ctx.author, ctx.guild, log_description, title="Log: Moderação", color=0xff0000
            )
            await self.client.log_to_channel(ctx.guild, log_embed, log_type="moderacao")

        except discord.Forbidden:
            await ctx.send("Eu não tenho permissão para banir este membro.", delete_after=10)
        except Exception as e:
            await ctx.send(f"Ocorreu um erro ao tentar banir o membro: {e}", delete_after=10)

    @ban.error
    async def ban_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.client.delete_message_user(ctx)
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{ctx.author.mention}, você não tem permissão para usar este comando.", delete_after=10)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"Eu preciso da permissão `Banir Membros` para executar este comando.", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Uso correto: `r.ban <@membro> [motivo]`", delete_after=10)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"Membro não encontrado. Tente novamente.", delete_after=10)
        else:
            print(f"Erro no comando r.ban: {error}")
            await ctx.send("Ocorreu um erro inesperado ao executar o comando.", delete_after=10)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Moderation(client))