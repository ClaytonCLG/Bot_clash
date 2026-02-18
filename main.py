import asyncio
import logging
import coc
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, COC_API_KEY, CLAN_TAG, TELEGRAM_CHAT_ID

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicializar cliente CoC
coc_client = coc.Client()

# --- COMANDOS DO TELEGRAM ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚀 Bot Dominadores BR Ativado!\nUse /help para ver os comandos.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = [
        "/clan - Status do clã",
        "/war - Resultado da última guerra",
        "/top_attackers - Melhores atacantes",
        "/donations - Ranking de doações"
    ]
    await update.message.reply_text("Comandos:\n" + "\n".join(commands))

async def get_clan_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        msg = (f"🏰 *Clã:* {clan.name}\n⭐ *Nível:* {clan.level}\n👥 *Membros:* {clan.member_count}/50\n🏆 *Pontos:* {clan.points}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

async def get_war_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        war = await coc_client.get_current_war(CLAN_TAG)
        if not war or war.state == "notInWar":
            await update.message.reply_text("Não há guerra em andamento.")
            return
        msg = (f"⚔️ *Guerra contra:* {war.opponent.name}\n⭐ *Estrelas:* {war.clan.stars} vs {war.opponent.stars}\n💥 *Destruição:* {war.clan.destruction:.2f}%")
        
        best_attack = None
        for attack in war.attacks:
            if not best_attack or (attack.stars > best_attack.stars) or (attack.stars == best_attack.stars and attack.destruction > best_attack.destruction):
                best_attack = attack
        if best_attack:
            attacker = next(m for m in war.clan.members if m.tag == best_attack.attacker_tag)
            msg += f"\n🔥 *Melhor Ataque:* {attacker.name} ({best_attack.stars}⭐, {best_attack.destruction}%)"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Erro na guerra: {e}")

async def get_top_attackers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        members = sorted(clan.members, key=lambda m: m.war_stars, reverse=True)
        msg = "🏆 *Melhores Atacantes:*\n"
        for i, m in enumerate(members[:10], 1):
            msg += f"{i}. {m.name} - {m.war_stars}⭐\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Erro no ranking: {e}")

async def get_donations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        clan = await coc_client.get_clan(CLAN_TAG)
        members = sorted(clan.members, key=lambda m: m.donations, reverse=True)
        msg = "🎁 *Ranking de Doações:*\n"
        for i, m in enumerate(members[:10], 1):
            msg += f"{i}. {m.name} - {m.donations} tropas\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Erro nas doações: {e}")

# --- MONITORAMENTO AUTOMÁTICO ---

async def run_monitor(application: Application):
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
            
            # Entrou
            for tag in current_member_tags - last_member_tags:
                member = next(m for m in clan.members if m.tag == tag)
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📥 **Novo Membro!**\n{member.name} entrou no clã.")
            
            # Saiu
            for tag in last_member_tags - current_member_tags:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📤 **Membro saiu!**\nTag: {tag} deixou o clã.")

            last_member_tags = current_member_tags
            await asyncio.sleep(300) # 5 minutos
        except Exception as e:
            logger.error(f"Erro no monitor: {e}")
            await asyncio.sleep(60)

async def main():
    await coc_client.login_with_tokens(COC_API_KEY)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clan", get_clan_info))
    application.add_handler(CommandHandler("war", get_war_info))
    application.add_handler(CommandHandler("top_attackers", get_top_attackers))
    application.add_handler(CommandHandler("donations", get_donations))

    # Rodar monitor em segundo plano
    asyncio.create_task(run_monitor(application))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Manter rodando
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
