# config.py

"""
Arquivo central de configurações.
Armazena IDs, nomes e outras constantes para facilitar a manutenção.
"""

# --- IDs de Usuários ---

import os


def _parse_id_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# IDs dos super administradores do bot, que ignoram cooldowns e têm acesso a comandos restritos.
SUPER_ADMIN_IDS = _parse_id_list(os.getenv("SUPER_ADMIN_IDS", ""))

# ID do desenvolvedor principal, que recebe o cargo especial.
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "0"))

# --- Nomes de Cargos ---
DEVELOPER_ROLE_NAME = "Desenvolvedor"