import asyncio
import logging
import coc
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, COC_API_KEY, CLAN_TAG, TELEGRAM_CHAT_ID
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Servidor Web simples para manter a Render feliz
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Online")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

# --- COMANDOS DO TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot Dominadores BR Ativado!")

async def get_war_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        war = await coc_client.get_current_war(CLAN_TAG)
        if not war or war.state == "notInWar":
            await update.message.reply_text("Não há guerra em andamento.")
            return
        msg = f"⚔️ Guerra contra: {war.opponent.name}\n⭐ Estrelas: {war.clan.stars} vs {war.opponent.stars}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

# --- MONITORAMENTO ---
async def run_monitor(application):
    bot = application.bot
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        last_member_tags = {m.tag for m in clan.members}
    except:
        last_member_tags = set()

    while True:
        try:
            clan = await coc_client.get_clan(CLAN_TAG)
            current_member_tags = {m.tag for m in clan.members}
            for tag in current_member_tags - last_member_tags:
                member = next(m for m in clan.members if m.tag == tag)
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📥 Novo Membro: {member.name}")
            for tag in last_member_tags - current_member_tags:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📤 Membro saiu (Tag: {tag})")
            last_member_tags = current_member_tags
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Erro no monitor: {e}")
            await asyncio.sleep(60)

async def main():
    global coc_client
    coc_client = coc.Client()
    try:
        await coc_client.login_with_tokens(COC_API_KEY)
    except Exception as e:
        logger.error(f"Erro login CoC: {e}")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("war", get_war_info))

    asyncio.create_task(run_monitor(application))
    
    # Iniciar servidor de saúde em outra thread
    threading.Thread(target=run_health_check, daemon=True).start()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
