import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_db(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving database: {e}")

# Cargar datos al inicio
db = load_db()

# --- MANEJADOR DE MENSAJES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    text = update.message.text.strip()

    if text.startswith('+') or text.startswith('*'):
        trigger = text[0]              # '+' o '*'
        content = text[1:].strip()     # lo que viene después
        db.append(trigger + content)
        save_db(db)
        await update.message.reply_text(f"✅ Guardado: {content}")

    elif text.startswith('-'):
        keyword = text[1:].strip().lower()
        removed = [e for e in db if keyword in e.lower()]
        if removed:
            db = [e for e in db if keyword not in e.lower()]
            save_db(db)
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
    # Guardar chat_id cuando alguien inicia el bot
    chat_id = str(update.effective_chat.id)
    with open("chat_id.txt", "w") as f:
        f.write(chat_id)
    await update.message.reply_text("📘 Bienvenido. Usa '+' para guardar eventos y '*' para eventos importantes.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos:\n+ evento → guardar evento normal\n* evento → evento importante\n- evento → borrar\nPregunta por persona o fecha.")

# --- ENVÍO AUTOMÁTICO A LAS 02:00 ---
async def send_daily_summary():
    global db
    now = datetime.datetime.now()
    today_str = now.strftime('%d %b').upper()
    in_14_days_str = (now + datetime.timedelta(days=14)).strftime('%d %b').upper()

    # Recargar datos por si acaso
    db = load_db()

    events_today = [e for e in db if e.startswith('+') and today_str in e.upper()]
    important_soon = [e for e in db if e.startswith('*') and in_14_days_str in e.upper()]

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

    if os.path.exists('chat_id.txt'):
        try:
            with open('chat_id.txt', 'r') as f:
                chat_id = f.read().strip()
                if chat_id:
                    # Obtener la aplicación desde el contexto global
                    from telegram import Bot
                    bot_token = os.getenv('BOT_TOKEN')
                    bot = Bot(token=bot_token)
                    await bot.send_message(chat_id=chat_id, text=message)
                    logging.info(f"Daily summary sent to {chat_id}")
        except Exception as e:
            logging.error(f"Error sending daily summary: {e}")

# --- FLASK PARA STATUS ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo ✅"

@app.route('/health')
def health():
    return {"status": "ok", "entries": len(db)}

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- FUNCIÓN PRINCIPAL ---
async def main():
    print("🤖 Iniciando el bot...")
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("❌ BOT_TOKEN no está definido en las variables de entorno.")

    # Crear aplicación
    application = ApplicationBuilder().token(bot_token).build()
    
    # Añadir handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Configurar scheduler usando AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_summary, 
        trigger='cron', 
        hour=2, 
        minute=0,
        timezone='Europe/Madrid'  # Ajusta según tu zona horaria
    )
    scheduler.start()
    
    print("✅ Scheduler iniciado")

    # Iniciar Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask iniciado")

    print("✅ Bot activo. Esperando mensajes...")
    
    # Iniciar el bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        # Mantener el bot corriendo
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Deteniendo el bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        scheduler.shutdown()

def run_bot():
    """Función para ejecutar el bot de forma síncrona"""
    asyncio.run(main())

if __name__ == '__main__':
    run_bot()
