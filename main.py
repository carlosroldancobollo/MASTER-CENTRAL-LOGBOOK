import logging
import json
import os
import threading
from telegram import Update, ReplyKeyboardMarkup
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

# Teclado personalizado
keyboard = [
    ['+', '-'],
    ['/all', '/import'],
    ['🔍 Buscar']
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Handlers del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Bot iniciado. Usa los botones de abajo o escribe:\n"
        "• + texto → guardar\n"
        "• - palabra → borrar\n"
        "• /all → ver todo\n"
        "• /import → importar datos\n"
        "• texto → buscar",
        reply_markup=reply_markup
    )

async def import_old_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    old_data = ["08 SEP Cumpleaños físico", "02 JUL Cumpleaños espiritual", "RUBI esta trabajando en montaje de escenarios en el wanda y montó el de acdc", "01 JAN Fiesta año nuevo", "06 JAN Fiesta de Reyes", "29 JAN Cumple ABUELOPACO", "30 JAN Cumple SACO", "09 FEB Cumple NORA", "12 FEB Cumple ANTONIO", "18 FEB Cumple BARBESA", "20 MAR Cumple REBECA", "29 MAR Cumple OLGA", "29 MAR Cumple PAQUI", "30 MAR Cumple ANA uf", "02 MAY Cumple MADRE", "24 MAY Cumple RUBI", "05 JUN Cumple HERMANO", "07 JUN Cumple PADRE", "12 JUL Cumple ABUELACHUS", "19 JUL Cumple WICHI", "22 JUL Cumple PAULA", "24 JUL Cumple VERA", "28 JUL Cumple ANGELSANTOS", "29 JUL Cumple MIKELSIUS", "15 AGO Cumple MIWI", "20 AGO Cumple AURELIO", "21 AGO Cumple ABBY", "23 AGO Cumple PABLEÑAS", "30 AGO Cumple ABUELOTOMAS", "09 SEP Cumple RODRO", "12 SEP Cumple ADRO", "22 SEP Cumple ABUELAMERI", "26 SEP Cumple CAMPER", "03 OCT Cumple VIWI", "17 OCT Cumple ISMA", "31 OCT Cumple MIKE", "03 NOV Cumple PABLOKODI", "09 NOV Cumple CESAR", "29 NOV Cumple TIOJOSE", "30 NOV Cumple ESPETO", "08 DEC Cumple LAURA", "25 DEC Cumple MARIN", "MIWI tiene una boda india de su prima en septiembre", "29 JUL Cumple HELENAPLANS", "24 JUN 2025 Muere la madre de ESPETO", "* 07 SEP 2023 Primer vuelo como cadete de piloto", "GOMEYO IRATI se va a francia el 21 AGO", "RUBI estuvo a finales de JUL en islas cíes de vacas", "LAURA cita a ciegas con un amigo de la novia de DIEGONAVARRO", "MIWI su hermano se quiere meter al ejercito, hizo pruebas sin preparar mucho pero no las paso", "ISMA trabajando en la residencia de la latina alto de extremadura. Su jefa maría es lesbiana que fuma y es una cabrona. No le gusta el ambiente entre compas y quiere hacer el master en algún momento", "06 AGO Cumple PORTI y PUCHIS", "PAULA se va a japon durante 21 dias en OCT", "MARINA ahora a finales de AGO le dicen si la han cogido de regidora en el rey leon", "HECTOR nombre hija candela", "+ VIWI esta a mediados de AGO en canada", "MIWI a mediados de AGO murio un hermano de su abuelo", "GOMEYO a mediados de AGO murio hermano abuela IRATI", "GOMEYO Cumple 01 APR", "ESPETO esta renovado en faunia hasta SEP", "NACHO hizo el C1 de ingles a mediados de AGO", "TIOJOSE pendiente de operacion de hernias en AGO", "ABUELACHUS pendiente de residencia", "MARTINAWI se fue de vacas la primera semana de AGO a gandia", "MARTINAWI se va el ultimo finde de AGO a ver a su novia a san sebastian"]
    
    # Añadir los datos antiguos evitando duplicados
    added_count = 0
    for item in old_data:
        if item not in db:
            db.append(item)
            added_count += 1
    
    save_db(db)
async def show_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db:
        await update.message.reply_text("📭 Base de datos vacía", reply_markup=reply_markup)
        return
    
    # Telegram tiene límite de 4096 caracteres por mensaje
    items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(db)])
    
    if len(items_text) <= 4000:  # Margen de seguridad
        await update.message.reply_text(f"📋 Base de datos ({len(db)} elementos):\n\n{items_text}", reply_markup=reply_markup)
    else:
        # Si es muy largo, dividir en chunks
        chunk_size = 3500
        chunks = [items_text[i:i+chunk_size] for i in range(0, len(items_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            header = f"📋 Base de datos (parte {i+1}/{len(chunks)}):\n\n" if i == 0 else f"📋 Continuación (parte {i+1}/{len(chunks)}):\n\n"
            await update.message.reply_text(header + chunk, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    text = update.message.text.strip()

    # Si pulsa el botón "🔍 Buscar", dar instrucciones
    if text == "🔍 Buscar":
        await update.message.reply_text("Escribe lo que quieres buscar:", reply_markup=reply_markup)
        return

    if text.startswith('+'):
        # Guardar
        content = text[1:].strip()
        if not content:
            await update.message.reply_text("Escribe después del + lo que quieres guardar:", reply_markup=reply_markup)
            return
        db.append(content)
        save_db(db)
        await update.message.reply_text(f"✅ Guardado: {content}", reply_markup=reply_markup)
    
    elif text.startswith('-'):
        # Borrar
        keyword = text[1:].strip().lower()
        if not keyword:
            await update.message.reply_text("Escribe después del - lo que quieres borrar:", reply_markup=reply_markup)
            return
        
        # Primero identificar qué se va a borrar
        items_to_remove = [item for item in db if keyword in item.lower()]
        
        if items_to_remove:
            # Quitar los elementos
            db = [item for item in db if keyword not in item.lower()]
            save_db(db)
            
            # Mostrar qué se borró
            removed_text = "\n".join([f"• {item}" for item in items_to_remove])
            await update.message.reply_text(f"❌ Borrado ({len(items_to_remove)} elementos):\n{removed_text}", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❗ No encontré nada para borrar", reply_markup=reply_markup)
    
    else:
        # Buscar
        results = [item for item in db if text.lower() in item.lower()]
        if results:
            response = "🔍 Encontrado:\n" + "\n".join(results[:10])  # Máximo 10 resultados
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            await update.message.reply_text("❓ No encontrado", reply_markup=reply_markup)

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
    app_bot.add_handler(CommandHandler("import", import_old_data))
    app_bot.add_handler(CommandHandler("all", show_all_data))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Flask en background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Bot iniciado")
    
    # Ejecutar bot
    app_bot.run_polling()

if __name__ == '__main__':
    main()
