# ================== Conferência Completa do Sistema de Safiras ==================

import os
import json
from datetime import datetime
import discord
from discord.ext import commands
from group import LOG_SAFIRA_ID, CARGO_MODERADOR_ID, SETORIAL_AUTO, SETORIAL_COMAND

ARQUIVO_SAFIRAS = "safiras.json"
ARQUIVO_LOG_SAFIRA = "log_safira.txt"



class SafiraCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.safiras = self._carregar_safiras()
        self._checar_arquivos_logs()

    # ---------------- Banco de Dados ---------------- #

    def _carregar_safiras(self):
        if not os.path.exists(ARQUIVO_SAFIRAS):
            with open(ARQUIVO_SAFIRAS, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
            return {}
        else:
            with open(ARQUIVO_SAFIRAS, "r", encoding="utf-8") as f:
                return json.load(f)

    def _checar_arquivos_logs(self):
        if not os.path.exists(ARQUIVO_LOG_SAFIRA):
            with open(ARQUIVO_LOG_SAFIRA, "w", encoding="utf-8") as f:
                f.write("=== LOG DE SAFIRAS ===\n")

    def salvar_safiras(self):
        with open(ARQUIVO_SAFIRAS, "w", encoding="utf-8") as f:
            json.dump(self.safiras, f, indent=4)

    def registrar_log_safira(self, acao: str):
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        log_msg = f"[{now}] {acao}"
        with open(ARQUIVO_LOG_SAFIRA, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        print(log_msg)

    # ---------------- Utilidades Auxiliares ---------------- #

    @staticmethod
    def remover_duplicados(membros):
        vistos = set()
        unicos = []
        for m in membros:
            if m.id not in vistos:
                vistos.add(m.id)
                unicos.append(m)
        return unicos

    # ---------------- Logs ---------------- #

    async def log_safira_embed(self, guild, membro, moderador, acao, quantidade, total, motivo, cargo_atual=None):
        canal = guild.get_channel(LOG_SAFIRA_ID)
        if not canal:
            return

        alteracao = (
            f"+{quantidade}" if acao in ("adds", "add") else
            f"-{quantidade}" if acao in ("revs", "remove") else
            "Zerado"
        )

        embed = discord.Embed(
            title="Registro de Safiras",
            color=discord.Color(int("ff0000", 16)),
        )
        embed.add_field(name="<:Z9_STAFF_RED:1414311653734088735>・STAFF:", value=membro.mention, inline=False)
        embed.add_field(name="<:Z9_DOC_RED:1414311649132675206>・Documentador(a):", value=moderador.mention, inline=False)
        embed.add_field(name="<:Z9_SAFIRA_RED:1414677775446638602>・Alteração:", value=alteracao, inline=False)
        embed.add_field(name="<:Z9_PIN_RED:1414311666836836432>・Quantidade Total:", value=f"{total} safiras.", inline=False)
        if cargo_atual:
            embed.add_field(name="<:Z9_TAG_RED:1414311680908722218>・Cargo Atual:", value=f"`{cargo_atual.name}`", inline=False)
        embed.add_field(name="<:Z9_DOC_RED:1414311660419809382>・Motivo:", value=motivo, inline=False)
        embed.set_footer(text=datetime.now().strftime("%d/%m/%Y às %H:%M"))
        await canal.send(embed=embed)
        self.registrar_log_safira(
            f"[LOG-SAFIRA] {moderador} fez {acao} em {membro} (ID: {membro.id}). "
            f"Quantidade: {quantidade}. Total: {total}. Motivo: {motivo}"
        )

    # ---------------- Utilidades ---------------- #

    @staticmethod
    def tem_cargo_moderador(membro):
        return any(role.id in CARGO_MODERADOR_ID for role in membro.roles)

    @staticmethod
    async def apagar_mensagem_usuario(ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @staticmethod
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

    # ---------------- Progressão Corrigida ---------------- #

    async def checar_progressao_safira(self, membro, moderador=None, motivo="Progressão automática"):
        guild = membro.guild
        total = self.safiras.get(str(membro.id), 0)

        # 1. Identificar cargos automáticos e manuais
        ids_cargos_auto = {cid for _, _, cid in SETORIAL_AUTO}
        ids_cargos_comando_total = {cid for _, _, cid in SETORIAL_COMAND}
        ids_cargos_manuais = ids_cargos_comando_total - ids_cargos_auto

        # Encontrar o requisito mínimo de safiras para o primeiro cargo manual
        min_safiras_para_manual = float('inf')
        cargos_manuais_ordenados = sorted(
            [c for c in SETORIAL_COMAND if c[2] in ids_cargos_manuais], key=lambda x: x[0]
        )
        if cargos_manuais_ordenados:
            min_safiras_para_manual = cargos_manuais_ordenados[0][0] # Geralmente 60

        # 2. Lógica de rebaixamento de cargos manuais
        cargos_manuais_do_membro = [role for role in membro.roles if role.id in ids_cargos_manuais]
        if cargos_manuais_do_membro:
            if total < min_safiras_para_manual:
                await membro.remove_roles(*cargos_manuais_do_membro, reason="Rebaixamento por safiras insuficientes")
            else:
                return

        # 3. Encontrar o cargo automático correto a ser atribuído
        cargo_a_ser_atribuido_id = None
        for min_s, _, cargo_id in reversed(SETORIAL_AUTO):
            if total >= min_s:
                cargo_a_ser_atribuido_id = cargo_id
                break

        # 4. Remover cargos automáticos antigos e add o novo se necessário
        cargos_para_remover = []
        cargo_atual_ja_existe = False
        for role in membro.roles:
            if role.id in ids_cargos_auto:
                if role.id == cargo_a_ser_atribuido_id:
                    cargo_atual_ja_existe = True
                else:
                    cargos_para_remover.append(role)

        if cargos_para_remover:
            await membro.remove_roles(*cargos_para_remover, reason="Atualização de cargo por safiras")

        if not cargo_atual_ja_existe and cargo_a_ser_atribuido_id:
            novo_cargo = guild.get_role(cargo_a_ser_atribuido_id)
            if novo_cargo:
                await membro.add_roles(novo_cargo, reason="Progressão automática de safiras")
                self.registrar_log_safira(
                    f"[CARGO] {membro} teve o cargo atualizado para {novo_cargo.name} ({novo_cargo.id}) por ter {total} safiras"
                )
                if moderador:
                    try:
                        canal = moderador.guild.get_channel(LOG_SAFIRA_ID)
                        if canal:
                            await canal.send(
                                f"<:Z9_SAFIRA_RED:1422668209915433142> {membro.mention} agora é **{novo_cargo.name}** "
                                f"por alcançar **{total} safiras**!"
                            )
                    except Exception as e:
                        print(f"Erro ao enviar mensagem de log de safira: {e}")

    # ---------------- Alterar Safiras ---------------- #

    async def alterar_safiras(self, ctx, membros, quantidade, acao, motivo="Não informado"):
        embeds = []
        autor = getattr(ctx, "author", None)
        guild = getattr(ctx, "guild", None)

        for membro in membros:
            if acao in ("adds", "add"):
                self.safiras[str(membro.id)] = self.safiras.get(str(membro.id), 0) + quantidade
            elif acao in ("revs", "remove"):
                self.safiras[str(membro.id)] = max(0, self.safiras.get(str(membro.id), 0) - quantidade)
            elif acao == "zerar":
                self.safiras[str(membro.id)] = 0

            self.salvar_safiras()
            total = self.safiras[str(membro.id)]

            cargo_atual = None
            for min_s, max_s, cargo_id in SETORIAL_AUTO:
                if min_s <= total <= max_s:
                    cargo_atual = guild.get_role(cargo_id)
                    break

            cargo_nome = cargo_atual.name if cargo_atual else "Nenhum"

            embed = discord.Embed(color=discord.Color(int("ff0000", 16)))
            embed.add_field(name="<:Z9_STAFF_RED:1414311653734088735>・STAFF:", value=membro.mention, inline=False)
            if autor:
                embed.add_field(name="<:Z9_DOC_RED:1414311649132675206>・Documentador(a):", value=autor.mention, inline=False)

            if acao in ("adds", "add"):
                embed.add_field(name="<:Z9_SAFIRA_RED:1422668209915433142>・Alteração:", value=f"+{quantidade} safiras", inline=False)
            elif acao in ("revs", "remove"):
                embed.add_field(name="<:Z9_SAFIRA_RED:1422668209915433142>・Alteração:", value=f"-{quantidade} safiras", inline=False)
            else:
                embed.add_field(name="<:Z9_SAFIRA_RED:1422668209915433142>・Alteração:", value="Zerado", inline=False)

            embed.add_field(name="<:Z9_PIN_RED:1414311666836836432>・Quantidade Total:", value=f"{total} safiras.", inline=False)
            embed.add_field(name="<:Z9_TAG_RED:1414311680908722218>・Cargo Atual:", value=f"`{cargo_nome}`", inline=False)
            embed.add_field(name="<:Z9_DOC_RED:1414311660419809382>・Motivo:", value=motivo, inline=False)
            embed.set_footer(text=datetime.now().strftime("%d/%m/%Y às %H:%M"))

            embeds.append(embed)

            if autor and guild:
                await self.log_safira_embed(guild, membro, autor, acao, quantidade, total, motivo, cargo_atual)
                await self.checar_progressao_safira(membro, autor, motivo)

        return embeds

# Instância global para uso em outros módulos
safira_instance = SafiraCog(None)

# Variável global que aponta para o dicionário de safiras da instância
safiras = safira_instance.safiras

# Funções globais para manipular safiras
def salvar_safiras():
    """Salva o banco de safiras no arquivo JSON"""
    safira_instance.salvar_safiras()

def registrar_log_safira(msg):
    """Registra uma mensagem no log de safiras"""
    safira_instance.registrar_log(msg)

async def setup(bot):
    await bot.add_cog(SafiraCog(bot))