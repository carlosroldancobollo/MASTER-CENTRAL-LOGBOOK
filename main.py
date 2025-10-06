import logging
import json
import os
import threading
import schedule
import time
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask
import subprocess

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base de datos simple
DATA_FILE = 'logbook.json'
BACKUP_DIR = 'backups'
AUTO_COMMIT_FILE = 'last_auto_commit.txt'

# Base de datos inicial actualizada
INITIAL_DATA = [
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
    "NACHO hizo el C1 de ingles a mediados de AGO",
    "TIOJOSE pendiente de operacion de hernias en AGO",
    "ABUELACHUS pendiente de residencia",
    "VIWI esta a mediados de AGO en canada",
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
    "MARINA abuelos joseangel y gelines, tios leandro y adriana taller de hidricos en Ordaliegu",
    "PIWI con 11 asignaturas curso 25-26 busca equilibrio entre estudios y gym",
    "MARTIN se va el 17 SEP a monaco con sus padres por trabajo",
    "CARLOTA Conflicto: enganchada emocionalmente, conducta agresiva y posesiva. Escalada de agresividad y comportamiento toxico. Conducta toxica sostenida. Señales de control, manipulacion y agresividad. Baja tolerancia ala frustracio . Necesidad constante de validacion interna. Reaccion impulsiva y emocional. Ataque de celos",
    "RECETA Sopa de ajo: Coger tres o 4 cabezas de ajo y freir con bastante aceite. Que se sumerjan. Dorandose se echan los teozos de pan durom remover un poco y echar 2 cucharadas de pimenton, remover y echar un huevo. Remover y echar agua a tope. Despues echar sal. Dejar ahi un rato y echar 2 o 3 cucharas grandes de almendra molida. Dejar que hierva y echarle 2huevos",
    "RUBI trabajando en la UAM",
    "ISMA le despidieron a mediados SEP porque la baja que cubría se acabó",
    "ISMA busando hacer master de trabajo social",
    "ESPETO empieza en SEP academia para preparar opos de profe de bio en OCT del 2027",
    "MIKE en practicas hizo una eutanasia a un conejo",
    "EFNOTEBOOK recordar pasar after t.o. checklist en w",
    "EFNOTEBOOK PBN para LNAV poner VNV antes de TOD y luego ir descendiendo con VS la que aparezca en la parta. Para LNAV/VNAV armar el modo APR tambien para que lleve el modo vertical",
    "EFNOTEBOOK con AP climb con FLC para ascender a 110kts y descenso a VS con la requerida",
    "ADRO no se va a granada y ahora busca trabajo",
    "HELENAPLANS su trabajo de analista contenta, los compis guays y mucho teletrabajo. Su jefe no va a la ofi en mas de un año. Bastante flexible",
    "MARIONA le encanta el entrecot miy poco hecho",
    "PORTI empieza bachiller de adultos el 27 SEP",
    "PORTI tiene compa de piso hasta diciembre que estudia mecanica aeronautica",
    "LAURA se va a sacar el carnet de moto",
    "LAURA hablando y quedó con pablo, que conocio en capi. Esta en alemania haciendo una mision y no le responde al movil",
    "PAULA conservatorio de musica pinto, violin con su profe de toda la vida y tres personas mas tocan individual y en conjunto",
    "PAQUI va a clases de piano los viernes por la tarde, estudia lenguaje musical y practica con piano. En casa teclado de paula",
    "VIWI se va a su pueblo de palencia a vivir durante OCT y NOV. Quiere desconectar y vivir el duelo de su padre"
]

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"DB loaded: {len(data)} items")
                return data
        except Exception as e:
            logger.error(f"Error loading DB: {e}")
            logger.info("Using initial data")
            return INITIAL_DATA.copy()
    else:
        logger.info("No DB found, using initial data")
        return INITIAL_DATA.copy()

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
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return None

def should_auto_commit():
    """Verificar si es hora de hacer auto-commit"""
    try:
        if os.path.exists(AUTO_COMMIT_FILE):
            with open(AUTO_COMMIT_FILE, 'r') as f:
                last_commit_str = f.read().strip()
                last_commit = datetime.fromisoformat(last_commit_str)
                
                # Auto-commit cada 3 días
                if datetime.now() - last_commit > timedelta(days=3):
                    return True
        else:
            # Primera vez, crear el archivo
            with open(AUTO_COMMIT_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
        return False
    except Exception as e:
        logger.error(f"Error checking auto-commit: {e}")
        return False

def update_script_with_current_data():
    """Actualizar el script con los datos actuales para el próximo deploy"""
    try:
        # Leer el script actual
        with open(__file__, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Crear la nueva lista de datos
        new_data = '[\n'
        for item in db:
            # Escapar comillas en los datos
            escaped_item = item.replace('"', '\\"')
            new_data += f'    "{escaped_item}",\n'
        new_data = new_data.rstrip(',\n') + '\n]'
        
        # Reemplazar INITIAL_DATA en el contenido
        import re
        pattern = r'INITIAL_DATA = \[.*?\]'
        replacement = f'INITIAL_DATA = {new_data}'
        
        updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Escribir el archivo actualizado
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"Script updated with {len(db)} current items")
        return True
    except Exception as e:
        logger.error(f"Error updating script: {e}")
        return False

def perform_auto_commit():
    """Realizar commit automático para forzar redeploy"""
    try:
        # Actualizar script con datos actuales
        if update_script_with_current_data():
            # Actualizar timestamp
            with open(AUTO_COMMIT_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
            
            logger.info("Auto-commit performed - data preserved for next deploy")
            return True
        return False
    except Exception as e:
        logger.error(f"Error in auto-commit: {e}")
        return False

# Cargar datos y estados de usuarios
db = load_db()
user_states = {}

# Verificar auto-commit al inicio
if should_auto_commit():
    logger.info("Auto-commit needed, updating script...")
    perform_auto_commit()

# Teclado personalizado principal
main_keyboard = [
    ['/guardar', '/borrar'],
    ['/all', '/export'],
    ['/backup', '/restore'],
    ['🔍 Buscar']
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
        "📘 Bienvenido/a al Logbook Central\n\n"
        "Comandos disponibles:\n"
        "• /guardar → Guardar información\n"
        "• /borrar → Eliminar información\n"
        "• /all → Ver toda la base de datos\n"
        "• /export → Exportar formato script\n"
        "• /backup → Backup completo\n"
        "• /export → Exportar para script\n"
        "• /restore → Restaurar desde backup\n"
        "• Escribir texto → Buscar información\n\n"
        f"📊 Base de datos actual: {len(db)} elementos",
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
    """Crear backup JSON con formato MMDDHHMM"""
    try:
        # Crear nombre de archivo con formato MMDDHHMM
        timestamp = datetime.now().strftime("%m%d%H%M")
        backup_filename = f"backup_{timestamp}.json"
        
        # Crear directorio si no existe
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        # Guardar backup
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        # Enviar archivo
        with open(backup_path, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=backup_filename,
                caption=f"💾 Backup creado\n📊 {len(db)} elementos\n🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
        
        await update.message.reply_text(
            f"✅ Backup guardado como: {backup_filename}\n"
            f"📁 Guarda este archivo para restaurar",
            reply_markup=main_reply_markup
        )
            
    except Exception as e:
        logger.error(f"Error en backup_command: {e}")
        await update.message.reply_text(
            "❌ Error al crear el backup",
            reply_markup=main_reply_markup
        )

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar archivo para restaurar backup"""
    user_id = update.effective_user.id
    user_states[user_id] = 'waiting_for_backup_file'
    await update.message.reply_text(
        "📁 Envía el archivo JSON de backup para restaurar la base de datos.\n"
        "⚠️ Esto sobrescribirá todos los datos actuales.",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar archivos enviados para restaurar backup"""
    user_id = update.effective_user.id
    
    if user_states.get(user_id) != 'waiting_for_backup_file':
        await update.message.reply_text(
            "No estoy esperando ningún archivo. Use /restore para restaurar un backup.",
            reply_markup=main_reply_markup
        )
        return
    
    try:
        file_name = update.message.document.file_name
        if not file_name.endswith('.json'):
            await update.message.reply_text(
                "❌ Por favor, envía un archivo JSON válido.",
                reply_markup=main_reply_markup
            )
            return
        
        file = await update.message.document.get_file()
        file_content = await file.download_as_bytearray()
        
        restored_data = json.loads(file_content.decode('utf-8'))
        
        create_backup()
        
        global db
        db = restored_data
        save_db(db)
        
        user_states[user_id] = 'normal'
        await update.message.reply_text(
            f"✅ Backup restaurado exitosamente\n"
            f"📊 {len(db)} elementos restaurados\n"
            f"📁 Archivo: {file_name}",
            reply_markup=main_reply_markup
        )
        
    except json.JSONDecodeError:
        await update.message.reply_text(
            "❌ Error: El archivo no es un JSON válido",
            reply_markup=main_reply_markup
        )
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        await update.message.reply_text(
            "❌ Error al restaurar el backup",
            reply_markup=main_reply_markup
        )

async def si_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_states.get(user_id) == 'confirming_delete' and 'delete_items' in context.user_data:
        create_backup()
        
        items_to_delete = context.user_data['delete_items']
        
        global db
        for item in items_to_delete:
            if item in db:
                db.remove(item)
        save_db(db)
        
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

async def show_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar base de datos numerada para lectura fácil"""
    if not db:
        await update.message.reply_text("📭 La base de datos está vacía", reply_markup=main_reply_markup)
        return
    
    # Formato numerado para lectura fácil
    items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(db)])
    
    if len(items_text) <= 4000:
        await update.message.reply_text(
            f"📋 Base de datos ({len(db)} elementos):\n\n{items_text}",
            reply_markup=main_reply_markup
        )
    else:
        # Dividir en chunks
        chunk_size = 3500
        chunks = [items_text[i:i+chunk_size] for i in range(0, len(items_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                header = f"📋 Base de datos (parte {i+1}/{len(chunks)}):\n\n"
            else:
                header = f"📋 Continuación (parte {i+1}/{len(chunks)}):\n\n"
            
            if i == len(chunks) - 1:
                await update.message.reply_text(header + chunk, reply_markup=main_reply_markup)
            else:
                await update.message.reply_text(header + chunk)

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exportar base de datos en formato listo para copiar al script"""
    if not db:
        await update.message.reply_text("📭 La base de datos está vacía", reply_markup=main_reply_markup)
        return
    
    # Crear formato listo para copiar al script
    code_format = "INITIAL_DATA = [\n"
    for item in db:
        escaped_item = item.replace('"', '\\"')
        code_format += f'    "{escaped_item}",\n'
    code_format = code_format.rstrip(',\n') + '\n]'
    
    # Dividir en chunks si es muy largo
    if len(code_format) <= 4000:
        await update.message.reply_text(
            f"💾 **EXPORT - FORMATO PARA SCRIPT**\n"
            f"📊 Total: {len(db)} elementos\n"
            f"📝 Copia todo desde INITIAL_DATA hasta el ] final\n\n"
            f"```python\n{code_format}\n```",
            parse_mode='Markdown',
            reply_markup=main_reply_markup
        )
    else:
        # Dividir en partes
        chunk_size = 3500
        chunks = []
        current_chunk = "INITIAL_DATA = [\n"
        
        for i, item in enumerate(db):
            escaped_item = item.replace('"', '\\"')
            line = f'    "{escaped_item}",\n'
            
            if len(current_chunk) + len(line) > chunk_size:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += line
        
        if current_chunk:
            chunks.append(current_chunk.rstrip(',\n') + '\n]')
        
        # Enviar chunks
        for i, chunk in enumerate(chunks):
            if i == 0:
                await update.message.reply_text(
                    f"💾 **EXPORT PARTE {i+1}/{len(chunks)}**\n"
                    f"📊 Total: {len(db)} elementos\n"
                    f"📝 Copia TODAS las partes en orden\n\n"
                    f"```python\n{chunk}\n```",
                    parse_mode='Markdown'
                )
            elif i == len(chunks) - 1:
                await update.message.reply_text(
                    f"💾 **EXPORT PARTE {i+1}/{len(chunks)} - FINAL**\n\n"
                    f"```python\n{chunk}\n```",
                    parse_mode='Markdown',
                    reply_markup=main_reply_markup
                )
            else:
                await update.message.reply_text(
                    f"💾 **EXPORT PARTE {i+1}/{len(chunks)}**\n\n"
                    f"```python\n{chunk}\n```",
                    parse_mode='Markdown'
                )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global db
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    current_state = user_states.get(user_id, 'normal')
    
    if current_state == 'waiting_to_save':
        db.append(text)
        save_db(db)
        user_states[user_id] = 'normal'
        await update.message.reply_text(
            f"✅ Guardado: \"{text}\"",
            reply_markup=main_reply_markup
        )
        
    elif current_state == 'waiting_to_delete':
        keyword = text.lower()
        items_to_delete = [item for item in db if keyword in item.lower()]
        
        if items_to_delete:
            context.user_data['delete_items'] = items_to_delete
            context.user_data['delete_keyword'] = keyword
            user_states[user_id] = 'confirming_delete'
            
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
        user_states[user_id] = 'normal'
        results = [item for item in db if text.lower() in item.lower()]
        if results:
            response = "🔍 Resultados encontrados:\n" + "\n".join(results[:10])
            await update.message.reply_text(response, reply_markup=main_reply_markup)
        else:
            await update.message.reply_text("❓ No se encontraron resultados", reply_markup=main_reply_markup)

# Flask para mantener vivo
app = Flask(__name__)

@app.route('/')
def home():
    return f"🤖 Bot Logbook Central - Activo 🚀<br>📊 {len(db)} elementos en DB<br>🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"

@app.route('/health')
def health():
    return {"status": "ok", "db_items": len(db), "timestamp": datetime.now().isoformat(), "uptime": "running"}

@app.route('/ping')
def ping():
    return {"ping": "pong", "time": datetime.now().isoformat(), "db_count": len(db)}

@app.route('/status')
def status():
    try:
        next_commit = "N/A"
        if os.path.exists(AUTO_COMMIT_FILE):
            with open(AUTO_COMMIT_FILE, 'r') as f:
                last_commit = datetime.fromisoformat(f.read().strip())
                next_commit = (last_commit + timedelta(days=3)).strftime('%d/%m/%Y %H:%M')
    except:
        pass
    
    return {
        "status": "active",
        "db_items": len(db),
        "last_update": datetime.now().isoformat(),
        "next_auto_commit": next_commit
    }

def run_flask():
    try:
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")
        time.sleep(5)
        run_flask()

def schedule_checker():
    """Verificar tareas programadas"""
    while True:
        try:
            if should_auto_commit():
                logger.info("Performing scheduled auto-commit...")
                perform_auto_commit()
            time.sleep(3600)  # Verificar cada hora
        except Exception as e:
            logger.error(f"Error in schedule checker: {e}")
            time.sleep(3600)

def main():
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("BOT_TOKEN no encontrado en las variables de entorno")
    
    logger.info(f"🚀 Iniciando Bot Logbook Central - DB: {len(db)} elementos")
    
    app_bot = ApplicationBuilder().token(bot_token).job_queue(None).build()
    
    # Handlers
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("guardar", guardar_command))
    app_bot.add_handler(CommandHandler("borrar", borrar_command))
    app_bot.add_handler(CommandHandler("si", si_command))
    app_bot.add_handler(CommandHandler("no", no_command))
    app_bot.add_handler(CommandHandler("all", show_all_data))
    app_bot.add_handler(CommandHandler("export", export_command))
    app_bot.add_handler(CommandHandler("backup", backup_command))
    app_bot.add_handler(CommandHandler("restore", restore_command))
    app_bot.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Handlers configurados correctamente")
    
    # Iniciar Flask en thread separado
    try:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info("🌐 Flask server iniciado")
        
        # Iniciar verificador de auto-commit
        schedule_thread = threading.Thread(target=schedule_checker, daemon=True)
        schedule_thread.start()
        logger.info("⏰ Auto-commit scheduler iniciado")
        
        time.sleep(3)
        
    except Exception as e:
        logger.error(f"Error iniciando servicios: {e}")
    
    logger.info("🤖 Iniciando bot polling...")
    
    # Ejecutar bot con recuperación automática
    try:
        app_bot.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot detenido manualmente")
    except Exception as e:
        logger.error(f"Error crítico en bot: {e}")
        time.sleep(10)
        logger.info("Reintentando iniciar bot...")
        try:
            app_bot.run_polling(drop_pending_updates=True)
        except Exception as e2:
            logger.error(f"Falló el reintento: {e2}")
            raise

if __name__ == '__main__':
    main()
