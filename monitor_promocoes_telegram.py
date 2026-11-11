#!/usr/bin/env python3
"""
Monitor de Promoções no Telegram (Notebook Gamer)
-------------------------------------------------
Este script conecta à sua conta do Telegram via Telethon (StringSession),
monitora grupos/canais de promoções em tempo real e envia alertas imediatos
através de um Bot próprio (para tocar notificação no celular mesmo com os
grupos silenciados).

Inclui um mini-servidor HTTP embutido na porta definida por PORT (padrão 8080)
para rodar gratuitamente 24h em serviços de nuvem como o Render (combinado com
UptimeRobot).

Dependência única:
    pip install telethon
"""

import asyncio
import json
import logging
import os
import re
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("MonitorPromocoes")

# =====================================================================
# 1. VARIÁVEIS DE AMBIENTE (Configure no Render ou direto aqui p/ teste)
# =====================================================================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
STRING_SESSION = os.getenv("STRING_SESSION", "").strip()

# Opcional (Recomendado): Token do seu Bot criado no @BotFather e seu Chat ID
# para receber notificação push real no celular.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MEU_CHAT_ID = os.getenv("MEU_CHAT_ID", "").strip()

# Opcional: Lista de usernames ou IDs dos grupos/canais separados por vírgula.
# Exemplo: "promocoesgames,ofertasps5,-1001234567890"
# Se deixar vazio, o script monitora TODOS os grupos e canais da sua conta.
CHATS_FILTRO_RAW = os.getenv("CHATS_MONITORADOS", "").strip()

# =====================================================================
# 2. REGRAS DE FILTRAGEM (APENAS NOTEBOOK GAMER E AFINS)
# =====================================================================
PADROES_INTERESSE = {
    "Notebook Gamer": re.compile(
        r"\b(notebooks?\s+gamer|notes?\s+gamer|laptops?\s+gamer|"
        r"acer\s+nitro|nitro\s+v15|nitro\s+5|predator\s+helios|"
        r"dell\s+g15|alienware|lenovo\s+loq|lenovo\s+legion|legion\s+5|legion\s+slim|"
        r"asus\s+tuf|rog\s+strix|rog\s+zephyrus|hp\s+victus|msi\s+katana|msi\s+cyborg|"
        r"notebooks?\b[^\n]{0,40}\b(rtx|gtx)\s*\d{4})\b",
        re.IGNORECASE,
    ),
}


def extrair_categorias_encontradas(texto: str) -> list[str]:
    """Verifica se o texto bate com alguma das categorias monitoradas."""
    if not texto:
        return []
    categorias = []
    for nome_categoria, regex in PADROES_INTERESSE.items():
        if regex.search(texto):
            categorias.append(nome_categoria)
    return categorias


def parsear_chats_monitorados(raw: str):
    """Converte a string CHATS_MONITORADOS em uma lista de IDs/usernames."""
    if not raw:
        return None
    lista = []
    for item in raw.split(","):
        limpo = item.strip().lstrip("@")
        if not limpo:
            continue
        if limpo.lstrip("-").isdigit():
            lista.append(int(limpo))
        else:
            lista.append(limpo)
    return lista if lista else None


# =====================================================================
# 3. ENVIO DE NOTIFICAÇÃO VIA BOT DO TELEGRAM
# =====================================================================
def enviar_alerta_bot(mensagem_html: str) -> bool:
    """Envia mensagem via Telegram Bot API usando apenas biblioteca padrão."""
    if not BOT_TOKEN or not MEU_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": MEU_CHAT_ID,
            "text": mensagem_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as exc:
        logger.error(f"Erro ao enviar notificação pelo Bot: {exc}")
        return False


# =====================================================================
# 4. MINI-SERVIDOR HTTP (KEEP-ALIVE PARA NUVEM GRATUITA / RENDER)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"OK - Monitor de Promocoes ativo (Notebook Gamer)"
        )

    def log_message(self, format, *args):
        # Silencia logs de cada ping HTTP para manter o console limpo
        return


def iniciar_servidor_keep_alive():
    porta = int(os.getenv("PORT", "8080"))
    servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Servidor HTTP Keep-Alive escutando na porta {porta}")


# =====================================================================
# 5. GERADOR DE SESSÃO (RODAR 1 VEZ NO SEU PC)
# =====================================================================
async def gerar_string_session_interativo():
    print("\n=== GERADOR DE STRING_SESSION DO TELETHON ===")
    api_id_input = input("Digite seu API_ID (de https://my.telegram.org): ").strip()
    api_hash_input = input("Digite seu API_HASH: ").strip()

    async with TelegramClient(StringSession(), int(api_id_input), api_hash_input) as client:
        sessao_gerada = client.session.save()
        me = await client.get_me()
        print("\n" + "=" * 65)
        print(f"Login realizado com sucesso como: {me.first_name} (ID: {me.id})")
        print("\nGuarde os valores abaixo para colar nas variáveis da nuvem:")
        print(f"\nMEU_CHAT_ID = {me.id}")
        print(f"\nSTRING_SESSION =\n{sessao_gerada}")
        print("=" * 65)
        print("\nATENÇÃO: Nunca compartilhe sua STRING_SESSION publicamente!\n")


# =====================================================================
# 6. LOOP PRINCIPAL DE MONITORAMENTO
# =====================================================================
async def iniciar_monitoramento():
    if not API_ID or not API_HASH or not STRING_SESSION:
        logger.error(
            "Variáveis API_ID, API_HASH ou STRING_SESSION não encontradas! "
            "Se for sua primeira vez, rode: python monitor_promocoes_telegram.py --gerar-sessao"
        )
        sys.exit(1)

    iniciar_servidor_keep_alive()

    chats_alvo = parsear_chats_monitorados(CHATS_FILTRO_RAW)
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    @client.on(events.NewMessage(chats=chats_alvo, incoming=True))
    async def handler_nova_mensagem(event):
        # Ignora mensagens privadas de pessoas ou bots (foca em grupos e canais)
        if event.is_private:
            return

        texto_msg = event.raw_text or ""
        categorias = extrair_categorias_encontradas(texto_msg)
        if not categorias:
            return

        chat = await event.get_chat()
        titulo_grupo = getattr(chat, "title", "Grupo/Canal")
        username_grupo = getattr(chat, "username", None)

        # Monta o link direto para a mensagem original
        if username_grupo:
            link_msg = f"https://t.me/{username_grupo}/{event.id}"
        else:
            chat_id_limpo = str(event.chat_id).replace("-100", "").lstrip("-")
            link_msg = f"https://t.me/c/{chat_id_limpo}/{event.id}"

        tags_str = " + ".join(categorias)
        logger.info(f"Promoção detectada [{tags_str}] em: {titulo_grupo}")

        # Escapa caracteres HTML básicos do texto da promoção
        texto_seguro = (
            texto_msg.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        alerta_html = (
            f"🚨 <b>PROMOÇÃO DETECTADA: {tags_str}</b>\n"
            f"📢 <b>Canal/Grupo:</b> {titulo_grupo}\n\n"
            f"{texto_seguro}\n\n"
            f"🔗 <a href='{link_msg}'>Abrir mensagem original no Telegram</a>"
        )

        # Envia pelo Bot (se configurado) ou salva nas Mensagens Salvas
        enviado = await asyncio.to_thread(enviar_alerta_bot, alerta_html)
        if not enviado:
            await client.send_message("me", alerta_html, parse_mode="html")

    await client.start()
    me = await client.get_me()
    escopo = f"grupos específicos ({chats_alvo})" if chats_alvo else "TODOS os grupos e canais"
    logger.info(
        f"Conectado como {me.first_name}. Monitorando {escopo} para Notebook Gamer..."
    )
    await client.run_until_disconnected()


if __name__ == "__main__":
    if "--gerar-sessao" in sys.argv:
        asyncio.run(gerar_string_session_interativo())
    else:
        asyncio.run(iniciar_monitoramento())
