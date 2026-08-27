# Red Staff — Discord Moderation Bot

Bot modular de moderação e gestão para servidores Discord, desenvolvido em Python com `discord.py`. Focado em equipes de staff (Red), oferece sistema de aniversários, envio agendado de mensagens, logs de eventos, controle de permissões e muito mais.

## Funcionalidades

- **Aniversários** — registro e mensagens automáticas de aniversário por servidor
- **Mensagens agendadas** — envio de DMs em massa por cargo, com agendamento recorrente (dias da semana)
- **Logs de eventos** — logs de canais, mensagens, cargos, entrada/saída de membros e moderação
- **Permissões configuráveis** — cargos de admin/moderador por servidor, configuráveis via comandos
- **Comandos de moderação** — ban, kick, entre outros, com checks de permissão
- **Interface rica** — embeds personalizáveis por servidor (cor, imagem, thumbnail) e botões interativos

## Tecnologias

- Python 3.10+
- [discord.py](https://github.com/Rapptz/discord-py)
- SQLite

## Configuração

1. Clone o repositório:
   ```bash
   git clone https://github.com/Wuzuy/red_staff_squarecloud.git
   cd red_staff_squarecloud
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` na raiz com as variáveis abaixo:
   ```env
   DISCORD_TOKEN=seu_token_aqui
   SUPER_ADMIN_IDS=id1,id2,id3
   DEVELOPER_ID=seu_id
   CALL_SERVERS_IDS=id1,id2
   CHAT_SERVERS_IDS=id1
   ```

4. Inicie o bot:
   ```bash
   python bot.py
   ```

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais informações.