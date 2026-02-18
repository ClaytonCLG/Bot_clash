import asyncio
import logging
import coc
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, COC_API_KEY, CLAN_TAG, TELEGRAM_CHAT_ID
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

coc_client = coc.Client()

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot Online")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

# --- RESPOSTAS INTELIGENTES E SIMPLES ---
async def responder_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower()
    
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        
        if "clã" in text or "cla" in text:
            msg = f"🏰 Clã: {clan.name}\n⭐ Nível: {clan.level}\n👥 Membros: {clan.member_count}/50\n🏆 Pontos: {clan.points}"
            await update.message.reply_text(msg)
            
        elif "guerra" in text:
            war = await coc_client.get_current_war(CLAN_TAG)
            if not war or war.state == "notInWar":
                await update.message.reply_text("Não estamos em guerra agora.")
            else:
                msg = f"⚔️ Guerra contra: {war.opponent.name}\n⭐ Placar: {war.clan.stars} x {war.opponent.stars}\n💥 Destruição: {war.clan.destruction:.2f}%"
                await update.message.reply_text(msg)
                
        elif "doações" in text or "doacao" in text:
            members = sorted(clan.members, key=lambda m: m.donations, reverse=True)
            msg = "🎁 Maiores Doadores:\n"
            for i, m in enumerate(members[:10], 1):
                msg += f"{i}. {m.name} - {m.donations} tropas\n"
            await update.message.reply_text(msg)

        elif "ranking" in text or "ataques" in text:
            members = sorted(clan.members, key=lambda m: m.war_stars, reverse=True)
            msg = "🏆 Top 10 Atacantes (Temporada):\n"
            for i, m in enumerate(members[:10], 1):
                msg += f"{i}. {m.name} - {m.war_stars} estrelas\n"
            await update.message.reply_text(msg)

        elif "estratégia" in text or "estrategia" in text:
            war = await coc_client.get_current_war(CLAN_TAG)
            if not war or war.state != "inWar":
                await update.message.reply_text("Precisa estar em guerra para eu bolar uma estratégia!")
                return
            
            msg = "🧠 ESTRATEGISTA DOMINADORES BR:\n\n"
            # Sugestão simples baseada em espelho e CV
            for i, member in enumerate(war.clan.members[:5], 1):
                target = war.opponent.members[i-1]
                msg += f"👤 {member.name} -> Alvo #{i} ({target.name})\n"
                msg += f"💡 Dica: CV{member.town_hall} vs CV{target.town_hall}. Use estratégia compatível!\n\n"
            msg += "⚠️ Lembre-se: Ataque quem você tem confiança para dar 3 estrelas!"
            await update.message.reply_text(msg)

        elif "ajuda" in text or "comandos" in text:
            msg = "Diga uma dessas palavras:\n- clã (status)\n- guerra (status da guerra)\n- doações (ranking de doação)\n- ranking (melhores atacantes)\n- estratégia (dicas de alvos)\n- eventos (o que tá rolando)"
            await update.message.reply_text(msg)
            
    except Exception as e:
        logger.error(f"Erro: {e}")

# --- MONITORAMENTO AUTOMÁTICO (EVENTOS E GUERRA) ---
async def run_monitor(application):
    bot = application.bot
    last_war_state = None
    
    while True:
        try:
            # Monitor de Guerra
            war = await coc_client.get_current_war(CLAN_TAG)
            if war and war.state == "inWar" and last_war_state != "inWar":
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚔️ A GUERRA COMEÇOU contra {war.opponent.name}!\nBora pro 100%!")
            
            # Aviso de fim de guerra (faltando 2h)
            if war and war.state == "inWar" and war.end_time.hours == 2:
                missing = [m.name for m in war.clan.members if not m.attacks]
                if missing:
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ FALTAM 2 HORAS! Ainda não atacaram: {', '.join(missing)}")

            last_war_state = war.state if war else None
            await asyncio.sleep(600)
        except: await asyncio.sleep(60)

async def main():
    try: await coc_client.login_with_tokens(COC_API_KEY)
    except: pass
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagens))
    asyncio.create_task(run_monitor(application))
    threading.Thread(target=run_health_check, daemon=True).start()
    await application.initialize(); await application.start(); await application.updater.start_polling()
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
