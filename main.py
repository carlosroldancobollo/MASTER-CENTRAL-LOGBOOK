import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import datetime
import json
import os
import threading

# --- CONFIGURACIÓN INICIAL ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

DATA_FILE = 'logbook.json'
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        db = json.load(f)
else:
    db = []

def save_db():
    with open(DATA_FILE, 'w') as f:
        json.dump(db, f)

# --- MANEJADOR DE MENSAJES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith('+') or text.startswith('*'):
        trigger = text[0]              # '+' o '*'
        content = text[1:].strip()     # lo que viene después
        db.append(trigger + content)   # guardamos sin el símbolo delante
        save_db()
        await update.message.reply_text(f"✅ Guardado: {content}")

    elif text.startswith('-'):
        keyword = text[1:].strip().lower()
        removed = [e for e in db if keyword in e.lower()]
        if removed:
            db[:] = [e for e in db if keyword not in e.lower()]
            save_db()
            await update.message.reply_text(f"❌ Data removed:\n" + "\n".join(removed))
        else:
            await update.message.reply_text("❗ No encontré nada para borrar.")

    else:
        results = [e for e in db if text.lower() in e.lower()]
        if results:
            await update.message.reply_text("▶️ \n" + "\n".join(results))
        else:
            await update.message.reply_text("❓ data not found")

# --- COMANDOS BÁSICOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Bienvenido. Usa '+' para guardar eventos y '*' para eventos importantes.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos:\n+ evento → guardar evento normal\n* evento → evento importante\n- evento → borrar\nPregunta por persona o fecha.")

# --- ENVÍO AUTOMÁTICO A LAS 02:00 ---
async def send_daily_summary(application):
    now = datetime.datetime.now()
    today_str = now.strftime('%d %b').upper()  # p.ej., "31 JUL"
    in_14_days_str = (now + datetime.timedelta(days=14)).strftime('%d %b').upper()

    try:
        with open(DATA_FILE, 'r') as f:
            entries = json.load(f)
    except FileNotFoundError:
        entries = []

    events_today = [e for e in entries if e.startswith('+') and today_str in e.upper()]
    important_soon = [e for e in entries if e.startswith('*') and in_14_days_str in e.upper()]

    message = f"📆 Resumen automático del {today_str}:\n"

    if events_today:
        message += "\n✅ Eventos de hoy:\n" + "\n".join(["- " + e[1:].strip() for e in events_today])
    else:
        message += "\n📭 No hay eventos normales para hoy."

    if important_soon:
        message += f"\n\n⚠️ En 14 días ({in_14_days_str}) tienes eventos importantes:\n"
        message += "\n".join(["🌟 " + e[1:].strip() for e in important_soon])
    else:
        message += "\n\n🟢 No hay eventos importantes dentro de 14 días."

    # Usa el primer chat_id conocido (lo guarda tras el primer mensaje recibido)
    if os.path.exists('chat_id.txt'):
        with open('chat_id.txt', 'r') as f:
            chat_id = f.read().strip()
            await application.bot.send_message(chat_id=chat_id, text=message)

# --- FLASK PARA STATUS ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- FUNCIÓN PRINCIPAL ---
def main():
    print("🤖 Iniciando el bot...")

    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("❌ BOT_TOKEN no está definido en las variables de entorno.")

    application = ApplicationBuilder().token(bot_token).build()

    # Guarda el chat_id del primer mensaje recibido
    async def save_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        if not os.path.exists("chat_id.txt"):
            with open("chat_id.txt", "w") as f:
                f.write(chat_id)
        await handle_message(update, context)

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_chat_id))

    # Tarea programada diaria a las 02:00
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_summary, trigger='cron', hour=2, minute=0, args=[application])
    scheduler.start()

    # Flask en segundo plano
    threading.Thread(target=run_flask).start()

    print("✅ Bot activo. Esperando mensajes.")
    application.run_polling()

if __name__ == '__main__':
    main()
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    main()  # <-- esta es tu función principal del bot
