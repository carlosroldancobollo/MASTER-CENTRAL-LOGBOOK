import logging
import json
import os
import threading
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base de datos simple
DATA_FILE = 'logbook.json'
BACKUP_DIR = 'backups'

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading DB: {e}")
            return []
    return []

def save_db(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"DB saved with {len(data)} items")
    except Exception as e:
        logger.error(f"Error saving DB: {e}")

def create_backup():
    """Crear backup de la base de datos"""
    try:
        # Crear directorio de backups si no existe
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Nombre del backup con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
        
        # Copiar datos actuales al backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return None

# Cargar datos y estados de usuarios
db = load_db()
user_states = {}  # Para manejar estados de conversación

# Teclado personalizado principal
main_keyboard = [
    ['/guardar', '/borrar'],
    ['/all', '/backup'],
    ['/import', '🔍 Buscar']
]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Teclado para confirmación
confirm_keyboard = [
    ['/si', '/no']
]
confirm_reply_markup = ReplyKeyboardMarkup(confirm_keyboard, resize_keyboard=True, one_time_keyboard=False)

# Handlers del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 'normal'
    await update.message.reply_text(
        "📘 Bienvenido. Use los comandos disponibles:\n\n"
        "• /guardar → Guardar información\n"
        "• /borrar → Eliminar información\n"
        "• /all → Ver toda la base de datos\n"
        "• /backup → Crear backup de seguridad\n"
        "• /import → Importar datos antiguos\n"
        "• Escribir texto → Buscar información",
        reply_markup=main_reply_markup
    )

async def guardar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 'waiting_to_save'
    await update.message.reply_text(
        "¿Qué información desea guardar?",
        reply_markup=ReplyKeyboardRemove()
    )

async def borrar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 'waiting_to_delete'
    await update.message.reply_text(
        "¿Qué información desea borrar?",
        reply_markup=ReplyKeyboardRemove()
    )

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Crear backup de la base de datos"""
    backup_file = create_backup()
    
    if backup_file:
        await update.message.reply_text(
            f"✅ Backup creado exitosamente\n"
            f"📁 Archivo: {os.path.basename(backup_file)}\n"
            f"📊 {len(db)} elementos respaldados",
            reply_markup=main_reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Error al crear el backup",
            reply_markup=main_reply_markup
        )

async def si_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_states.get(user_id) == 'confirming_delete' and 'delete_items' in context.user_data:
        # Crear backup antes de borrar
        backup_file = create_backup()
        
        # Proceder con el borrado
        items_to_delete = context.user_data['delete_items']
        
        global db
        # Remover los elementos específicos
        for item in items_to_delete:
            if item in db:
                db.remove(item)
        save_db(db)
        
        # Mostrar qué se borró
        if len(items_to_delete) == 1:
            await update.message.reply_text(
                f"✅ Borrado: \"{items_to_delete[0]}\"",
                reply_markup=main_reply_markup
            )
        else:
            deleted_text = "\n".join([f"• {item}" for item in items_to_delete])
            await update.message.reply_text(
                f"✅ Borrado ({len(items_to_delete)} elementos):\n{deleted_text}",
                reply_markup=main_reply_markup
            )
        
        # Limpiar estado
        user_states[user_id] = 'normal'
        context.user_data.clear()
    else:
        await update.message.reply_text(
            "No hay ninguna acción pendiente de confirmación.",
            reply_markup=main_reply_markup
        )

async def no_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_states.get(user_id) == 'confirming_delete':
        # Volver a preguntar qué borrar
        user_states[user_id] = 'waiting_to_delete'
        await update.message.reply_text(
            "¿Qué información desea borrar?",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
    else:
        user_states[user_id] = 'normal'
        await update.message.reply_text(
            "Operación cancelada.",
            reply_markup=main_reply_markup
        )

async def import_old_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    old_data = [
        "08 SEP Cumpleaños físico",
        "02 JUL Cumpleaños espiritual",
        "RUBI esta trabajando en montaje de escenarios en el wanda y montó el de acdc",
        "01 JAN Fiesta año nuevo",
        "06 JAN Fiesta de Reyes",
        "29 JAN Cumple ABUELOPACO",
        "30 JAN Cumple SACO",
        "09 FEB Cumple NORA",
        "12 FEB Cumple ANTONIO",
        "18 FEB Cumple BARBESA",
        "20 MAR Cumple REBECA",
        "29 MAR Cumple OLGA",
        "29 MAR Cumple PAQUI",
        "30 MAR Cumple ANA uf",
        "02 MAY Cumple MADRE",
        "24 MAY Cumple RUBI",
        "05 JUN Cumple HERMANO",
        "07 JUN Cumple PADRE",
        "12 JUL Cumple ABUELACHUS",
        "19 JUL Cumple WICHI",
        "22 JUL Cumple PAULA",
        "24 JUL Cumple VERA",
        "28 JUL Cumple ANGELSANTOS",
        "29 JUL Cumple MIKELSIUS",
        "15 AGO Cumple MIWI",
        "20 AGO Cumple AURELIO",
        "21 AGO Cumple ABBY",
        "23 AGO Cumple PABLEÑAS",
        "30 AGO Cumple ABUELOTOMAS",
        "09 SEP Cumple RODRO",
        "12 SEP Cumple ADRO",
        "22 SEP Cumple ABUELAMERI",
        "26 SEP Cumple CAMPER",
        "03 OCT Cumple VIWI",
        "17 OCT Cumple ISMA",
        "31 OCT Cumple MIKE",
        "03 NOV Cumple PABLOKODI",
        "09 NOV Cumple CESAR",
        "29 NOV Cumple TIOJOSE",
        "30 NOV Cumple ESPETO",
        "08 DEC Cumple LAURA",
        "25 DEC Cumple MARIN",
        "MIWI tiene una boda india de su prima en septiembre",
        "29 JUL Cumple HELENAPLANS",
        "24 JUN 2025 Muere la madre de ESPETO",
        "* 07 SEP 2023 Primer vuelo como cadete de piloto",
        "GOMEYO IRATI se va a francia el 21 AGO",
        "RUBI estuvo a finales de JUL en islas cíes de vacas",
        "LAURA cita a ciegas con un amigo de la novia de DIEGONAVARRO",
        "MIWI su hermano se quiere meter al ejercito, hizo pruebas sin preparar mucho pero no las paso",
        "ISMA trabajando en la residencia de la latina alto de extremadura. Su jefa maría es lesbiana que fuma y es una cabrona. No le gusta el ambiente entre compas y quiere hacer el master en algún momento",
        "06 AGO Cumple PORTI y PUCHIS",
        "PAULA se va a japon durante 21 dias en OCT",
        "MARINA ahora a finales de AGO le dicen si la han cogido de regidora en el rey leon",
        "HECTOR nombre hija candela",
        "MIWI a mediados de AGO murio un hermano de su abuelo",
        "GOMEYO a mediados de AGO murio hermano abuela IRATI",
        "GOMEYO Cumple 01 APR",
        "ESPETO esta renovado en faunia hasta SEP",
        "NACHO hizo el C1 de ingles a mediados de AGO",
        "TIOJOSE pendiente de operacion de hernias en AGO",
        "ABUELACHUS pendiente de residencia",
        "MARTINAWI se fue de vacas la primera semana de AGO a gandia",
        "MARTINAWI se va el ultimo finde de AGO a ver a su novia a san sebastian",
        "VIWI esta a mediados de AGO en canada",
        "LAURA busca hacer opos para guardia forestal mejor que para seprona",
        "PAULA a japon del 25 OCT al 14 NOV",
        "PAULA patinaje hielo federada, competiciones por españa, especialmente logroño",
        "PAULA escucha podcast la ruina para comer y comparte cuentas de aprime, netf y hbo con su padre y madre",
        "CESAR en SEP comienza musta de aeropuertos, dividido en dos años para compatibilizar ineco",
        "CESAR hermana PATRI comienza modulo de enfermeria",
        "MIWI pedir contar relato",
        "MARINA contratada de regidora en elreyleon de mie a dom",
        "VIWI montreal su ciudad top 2 internac",
        "HELENAPLANS comienza en SEP trabajo de analista de datos en bcn",
        "HELENAPLANS se va a comprar un piso con su novio a finales 2025",
        "VIWI en canada premio a mejor investigacion estudiante",
        "MARINA abuelos joseangel y gelines, tios leandro y adriana taller de hidricos en ordaliegu",
        "PIWI con 11 asignaturas curso 25-26 busca equilibrio entre estudios y gym"
    ]
    
    # Crear backup antes de importar
    create_backup()
    
    # Añadir los datos antiguos evitando duplicados
    added_count = 0
    for item in old_data:
        if item not in db:
            db.append(item)
            added_count += 1
    
    save_db(db)
    await update.message.reply_text(
        f"📥 Se han importado {added_count} elementos de la base de datos antigua. Total: {len(db)} elementos.",
        reply_markup=main_reply_markup
    )

async def show_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db:
        await update.message.reply_text("📭 La base de datos está vacía", reply_markup=main_reply_markup)
        return
    
    # Telegram tiene límite de 4096 caracteres por mensaje
    items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(db)])
    
    if len(items_text) <= 4000:  # Margen de seguridad
        await update.message.reply_text(
            f"📋 Base de datos ({len(db)} elementos):\n\n{items_text}",
            reply_markup=main_reply_markup
        )
    else:
        # Si es muy largo, dividir en chunks
        chunk_size = 3500
        chunks = [items_text[i:i+chunk_size] for i in range(0, len(items_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            header = f"📋 Base de datos (parte {i+1}/{len(chunks)}):\n\n" if i == 0 else f"📋 Continuación (parte {i+1}/{len(chunks)}):\n\n"
            if i == len(chunks) - 1:  # Última parte
                await update.message.reply_text(header + chunk, reply_markup=main_reply_markup)
            else:
                await update.message.reply_text(header + chunk)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    current_state = user_states.get(user_id, 'normal')
    
    # Manejar estados específicos
    if current_state == 'waiting_to_save':
        # El usuario está enviando información para guardar
        db.append(text)
        save_db(db)
        user_states[user_id] = 'normal'
        await update.message.reply_text(
            f"✅ Guardado: \"{text}\"",
            reply_markup=main_reply_markup
        )
        
    elif current_state == 'waiting_to_delete':
        # El usuario está enviando información para borrar
        keyword = text.lower()
        items_to_delete = [item for item in db if keyword in item.lower()]
        
        if items_to_delete:
            # Guardar información para confirmación
            context.user_data['delete_items'] = items_to_delete
            context.user_data['delete_keyword'] = keyword
            user_states[user_id] = 'confirming_delete'
            
            # Mostrar qué se encontró y pedir confirmación
            items_text = "\n".join([f"• {item}" for item in items_to_delete])
            await update.message.reply_text(
                f"Se encontraron {len(items_to_delete)} elementos que coinciden:\n{items_text}\n\n"
                f"¿Desea proceder con el borrado?",
                reply_markup=confirm_reply_markup
            )
        else:
            await update.message.reply_text(
                f"No se encontró ningún elemento que contenga \"{text}\"",
                reply_markup=main_reply_markup
            )
            user_states[user_id] = 'normal'
    
    elif text == "🔍 Buscar":
        await update.message.reply_text("Escriba lo que desea buscar:", reply_markup=main_reply_markup)
        
    else:
        # Búsqueda normal
        user_states[user_id] = 'normal'
        results = [item for item in db if text.lower() in item.lower()]
        if results:
            response = "🔍 Resultados encontrados:\n" + "\n".join(results[:10])  # Máximo 10 resultados
            await update.message.reply_text(response, reply_markup=main_reply_markup)
        else:
            await update.message.reply_text("❓ No se encontraron resultados", reply_markup=main_reply_markup)

# Flask para mantener vivo
app = Flask(__name__)

@app.route('/')
def home():
    return f"Bot activo - {len(db)} elementos en DB"

@app.route('/health')
def health():
    return {"status": "ok", "db_items": len(db), "timestamp": datetime.now().isoformat()}

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

# Main
def main():
    # Token
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")
    
    logger.info("Iniciando aplicación...")
    logger.info(f"DB inicial: {len(db)} elementos")
    
    # Crear aplicación SIN JobQueue
    app_bot = ApplicationBuilder().token(bot_token).job_queue(None).build()
    
    # Handlers
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("guardar", guardar_command))
    app_bot.add_handler(CommandHandler("borrar", borrar_command))
    app_bot.add_handler(CommandHandler("si", si_command))
    app_bot.add_handler(CommandHandler("no", no_command))
    app_bot.add_handler(CommandHandler("all", show_all_data))
    app_bot.add_handler(CommandHandler("backup", backup_command))
    app_bot.add_handler(CommandHandler("import", import_old_data))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Handlers configurados correctamente")
    
    # Flask en background
    try:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info("Flask thread iniciado")
        
        # Pequeña espera para que Flask arranque
        import time
        time.sleep(2)
        
    except Exception as e:
        logger.error(f"Error iniciando Flask: {e}")
    
    logger.info("Iniciando bot polling...")
    
    # Ejecutar bot
    try:
        app_bot.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error en bot polling: {e}")
        raise

if __name__ == '__main__':
    main()
