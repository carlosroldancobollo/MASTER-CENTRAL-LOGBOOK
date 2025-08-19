import logging
import json
import os
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base de datos simple
DATA_FILE = 'logbook.json'

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_db(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving: {e}")

# Cargar datos
db = load_db()

# Handlers del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Bot iniciado. Usa + para guardar, - para borrar, o busca texto.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    text = update.message.text.strip()

    if text.startswith('+'):
        # Guardar
        content = text[1:].strip()
        db.append(content)
        save_db(db)
        await update.message.reply_text(f"✅ Guardado: {content}")
    
    elif text.startswith('-'):
        # Borrar
        keyword = text[1:].strip().lower()
        # Primero identificar qué se va a borrar
        items_to_remove = [item for item in db if keyword in item.lower()]
        
        if items_to_remove:
            # Quitar los elementos
            db = [item for item in db if keyword not in item.lower()]
            save_db(db)
            
            # Mostrar qué se borró
            removed_text = "\n".join([f"• {item}" for item in items_to_remove])
            await update.message.reply_text(f"❌ Borrado ({len(items_to_remove)} elementos):\n{removed_text}")
        else:
            await update.message.reply_text("❗ No encontré nada para borrar")
    
    else:
        # Buscar
        results = [item for item in db if text.lower() in item.lower()]
        if results:
            response = "🔍 Encontrado:\n" + "\n".join(results[:10])  # Máximo 10 resultados
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❓ No encontrado")

# Flask para mantener vivo
app = Flask(__name__)

@app.route('/')
def home():
    return f"Bot activo - {len(db)} elementos en DB"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

# Main
def main():
    # Token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("BOT_TOKEN no encontrado")
    
    # Crear aplicación SIN JobQueue
    app_bot = ApplicationBuilder().token(bot_token).job_queue(None).build()
    
    # Handlers
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Flask en background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Bot iniciado")
    
    # Ejecutar bot
    app_bot.run_polling()

if __name__ == '__main__':
    main()
