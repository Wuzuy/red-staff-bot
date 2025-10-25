import discord
from discord.ext import commands
from datetime import datetime, timezone
import json
from group import CARGO_MODERADOR_ID, SETORIAL_COMAND, LOG_SAFIRA_ID
from safira import ARQUIVO_SAFIRAS

def registrar_log(msg):
    try:
        with open("log_notificacao.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}\n")
    except Exception as e:
        print(f"[Log Error] {e}")
    print(msg)

def tem_cargo_moderador(membro):
    return any(role.id in CARGO_MODERADOR_ID for role in membro.roles)

async def apagar_mensagem_usuario(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

async def converter_membro(ctx, arg):
    try:
        return await commands.MemberConverter().convert(ctx, arg)
    except Exception:
        try:
            user_id = int(arg)
            membro = ctx.guild.get_member(user_id)
            if not membro:
                membro = await ctx.guild.fetch_member(user_id)
            return membro
        except Exception:
            return None

class UpSetorialCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="upsetorial")
    async def upsetorial(self, ctx, membro: str = None):
        await apagar_mensagem_usuario(ctx)

        # Verifica se o autor tem permissão
        if not tem_cargo_moderador(ctx.author):
            await ctx.send(
                "Você não tem permissão para usar este comando.",
                delete_after=15
            )
            return

        if not membro:
            await ctx.send(
                "Uso correto: `r.upsetorial [@membro ou ID]`",
                delete_after=15
            )
            return

        membro_obj = await converter_membro(ctx, membro)
        if not membro_obj:
            await ctx.send(
                "Usuário não encontrado.",
                delete_after=15
            )
            return

        # Carrega os dados de safiras
        try:
            with open(ARQUIVO_SAFIRAS, "r", encoding="utf-8") as f:
                safiras = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            safiras = {}

        total_safiras = safiras.get(str(membro_obj.id), 0)
        guild = ctx.guild

        # Define cargo correto baseado SOMENTE em SETORIAL_COMAND
        novo_cargo_id = None
        for min_s, max_s, cargo_id in SETORIAL_COMAND:
            if min_s <= total_safiras <= max_s:
                novo_cargo_id = cargo_id
                break

        # Se não tiver safiras suficientes, remove apenas cargos do grupo COMAND
        if not novo_cargo_id:
            for _, _, cid in SETORIAL_COMAND:
                cargo = guild.get_role(cid)
                if cargo and cargo in membro_obj.roles:
                    await membro_obj.remove_roles(cargo)

            await ctx.send(
                f"{membro_obj.mention} não possui safiras suficientes para ter cargo setorial.",
                delete_after=15
            )
            return

        novo_cargo = guild.get_role(novo_cargo_id)
        if not novo_cargo:
            await ctx.send(
                "Cargo correspondente não encontrado.",
                delete_after=15
            )
            return

        # Remove todos os cargos anteriores do grupo COMAND (não toca em outros sistemas)
        for _, _, cid in SETORIAL_COMAND:
            cargo = guild.get_role(cid)
            if cargo and cargo in membro_obj.roles and cargo.id != novo_cargo_id:
                await membro_obj.remove_roles(cargo)

        # Adiciona o novo cargo se ainda não tiver
        if novo_cargo not in membro_obj.roles:
            await membro_obj.add_roles(novo_cargo)
            msg_confirm = f"{membro_obj.mention} foi promovido(a) para {novo_cargo.mention}!"
        else:
            msg_confirm = f"{membro_obj.mention} já possui o cargo correto {novo_cargo.mention}."

        # Cria e envia o log embed
        embed = discord.Embed(
            title="Up Setorial",
            color=discord.Color.from_str("#ff0000"),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="Staff:",
            value=membro_obj.mention,
            inline=False
        )
        embed.add_field(
            name="Documentador(a):",
            value=ctx.author.mention,
            inline=False
        )
        embed.add_field(
            name="Safiras Totais:",
            value=f"{total_safiras} safiras",
            inline=False
        )
        embed.add_field(
            name="Cargo Atualizado:",
            value=novo_cargo.mention,
            inline=False
        )
        embed.set_footer(text=datetime.now().strftime("%d/%m/%Y às %H:%M"))

        canal_log = guild.get_channel(LOG_SAFIRA_ID)
        if canal_log:
            await canal_log.send(embed=embed)

        await ctx.send(msg_confirm, delete_after=15)

        # Log local (terminal)
        registrar_log(
            f"[UPA-SETORIAL] {ctx.author} atualizou o cargo setorial de {membro_obj} "
            f"para {novo_cargo.name} ({novo_cargo.id}) com {total_safiras} safiras."
        )

async def setup(bot):
    await bot.add_cog(UpSetorialCog(bot))