# telegram_pizzeria_bot.py
# Fecha: 30 de Mayo, 2025 (CORRECCIÓN V2 de logging: Suprimir LLM Request/Response detallados)
# Integración con ADK PizzeríaBot (Enfoque 2.1 - RootAgent central, Menú PDF)

import asyncio
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv, find_dotenv
import json # Para parsear la respuesta de la herramienta si es necesario
import httpx
import time

# Importar componentes ADK
# Asegúrate que pizzeria_agents.py esté en la misma carpeta o en el PYTHONPATH
from pizzeria_agents import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.adk.events import Event # Para inspeccionar eventos si es necesario
from telegram.ext import Application
from httpx import Request, Timeout # Importa Timeout

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Nivel INFO por defecto para menos verbosidad. Cambiar a DEBUG para ver detalles de eventos ADK.
)
logger = logging.getLogger(__name__)

# --- AJUSTE CLAVE: Reducir la verbosidad de los logs internos de Google ADK LLM ---
logging.getLogger('google_adk.google.adk.models.google_llm').setLevel(logging.WARNING)
logging.getLogger('google_adk.google.adk.tools.function_parameter_parse_util').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.WARNING) # Para requests HTTP
logging.getLogger('gspread').setLevel(logging.WARNING) # Para sheets_client

# --- Configuración del Bot de Telegram y ADK ---
env_path = find_dotenv(usecwd=True)
if env_path:
    logger.info(f"Archivo .env encontrado en: {env_path}")
    load_dotenv(dotenv_path=env_path, verbose=True)
else:
    logger.info("Archivo .env NO encontrado. Asegúrate que las variables de entorno estén configuradas globalmente o en el script.")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # ADK lo usa implícitamente

if not TELEGRAM_BOT_TOKEN:
    logger.critical("¡Error Crítico! TELEGRAM_BOT_TOKEN no encontrado. El bot no puede iniciar.")
    exit()
if not GOOGLE_API_KEY or GOOGLE_API_KEY == "TU_API_KEY_DE_GEMINI_AQUI": # Placeholder check
    logger.warning("¡Advertencia! GOOGLE_API_KEY no configurada o es un placeholder. Los agentes ADK podrían no funcionar.")

# Define un timeout más largo para las solicitudes HTTPX (ej. 20 segundos)
# El timeout se pasa al cliente HTTPX subyacente, no directamente a Request.
MAX_TELEGRAM_RETRIES = 5  # Máximo de reintentos a nivel de Telegram para un solo mensaje del usuario
INITIAL_BACKOFF_SECONDS = 2 # Tiempo de espera inicial para el backoff exponencial (se duplica en cada reintento)
# Construye la aplicación, pasando el timeout al cliente HTTPX
application = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .connect_timeout(30.0)  # Timeout de conexión en segundos
    .read_timeout(30.0)     # Timeout de lectura en segundos (importante para long polling)
    .write_timeout(30.0)    # Timeout de escritura en segundos
    .http_version("1.1")
    .build()
)
# Nombre del archivo PDF del menú (debe estar en la misma carpeta que este script)
MENU_PDF_FILENAME = "menu_pizzeria.pdf"

# Configuración de ADK
APP_NAME_ADK = "PizzeriaChatBot_Telegram_v2_1"
session_service_adk = InMemorySessionService()
runner_adk = Runner(agent=root_agent, app_name=APP_NAME_ADK, session_service=session_service_adk)

# Ajustar max_output_tokens para todos los agentes (si es necesario)
common_generate_config = genai_types.GenerateContentConfig(max_output_tokens=8192)
# Aplicar a root_agent y sus sub_agents si los tiene definidos y son LlmAgent
def apply_config_recursively(agent_instance, config):
    if hasattr(agent_instance, 'generate_content_config'):
        if not agent_instance.generate_content_config:
            agent_instance.generate_content_config = config
        elif agent_instance.generate_content_config.max_output_tokens is None or \
             agent_instance.generate_content_config.max_output_tokens < config.max_output_tokens:
            agent_instance.generate_content_config.max_output_tokens = config.max_output_tokens
    if hasattr(agent_instance, 'sub_agents') and agent_instance.sub_agents:
        for sub_agent in agent_instance.sub_agents:
            apply_config_recursively(sub_agent, config)

apply_config_recursively(root_agent, common_generate_config)
logger.info(f"Configuración de max_output_tokens aplicada a los agentes.")


async def get_or_create_adk_session(user_id_telegram: int, chat_id_telegram: int):
    """Obtiene o crea una sesión ADK, asegurando que el estado inicial sea correcto."""
    user_id_adk = str(user_id_telegram) 
    session_id_adk = str(chat_id_telegram)

    current_session = await session_service_adk.get_session(
        app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk
    )
    if current_session is None:
        logger.info(f"No se encontró sesión para user {user_id_adk}. Creando una nueva...")
        
        # <<< ESTE ES EL BLOQUE CORREGIDO Y LA SOLUCIÓN CLAVE >>>
        initial_state = {
            '_session_user_id': user_id_adk,                # AÑADIDO: Guarda el ID del usuario.
            'processing_order_sub_phase': 'A_GESTION_CLIENTE', # AÑADIDO: Establece la fase inicial.
            'current_main_goal': 'IDLE'                     # Establece un objetivo inicial.
        }
        
        current_session = await session_service_adk.create_session(
            app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk, state=initial_state
        )
        logger.info(f"Nueva sesión ADK creada para user {user_id_adk}. Estado inicial: {initial_state}")
    
    else:
        # Nos aseguramos que el user_id siempre esté, incluso en sesiones existentes.
        if current_session.state is None:
            current_session.state = {}
        current_session.state['_session_user_id'] = user_id_adk
        logger.info(f"Sesión ADK existente recuperada para user {user_id_adk}. Estado actual: {current_session.state}")
        
    return user_id_adk, session_id_adk

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto del usuario y las acciones especiales, con lógica de reintentos."""
    if not update.message or not update.message.text:
        return

    user_id_telegram = update.effective_user.id
    chat_id_telegram = update.effective_chat.id
    user_message_text = update.message.text # Se guarda el texto original para reintentos

    logger.info(f"💬 Mensaje del usuario {user_id_telegram} en chat {chat_id_telegram}: '{user_message_text}'")

    user_id_adk, session_id_adk = await get_or_create_adk_session(user_id_telegram, chat_id_telegram)
    
    agent_final_response_text = "Lo siento, estoy teniendo algunos problemas para procesar tu solicitud en este momento."
    action_to_perform_by_telegram_bot = None
    pdf_to_send = None
    message_before_pdf = None

    telegram_retry_count = 0 # Contador de reintentos a nivel de Telegram para este mensaje

    # --- Bucle principal de reintentos ---
    while telegram_retry_count < MAX_TELEGRAM_RETRIES:
        logger.info(f"🔄 [Telegram_Loop] Procesando mensaje (Intento {telegram_retry_count + 1}/{MAX_TELEGRAM_RETRIES}) para user {user_id_adk}, session {session_id_adk}")
        
        # Preparar el mensaje del usuario para ADK en cada intento (por si el objeto Content se consume)
        adk_message = genai_types.Content(parts=[genai_types.Part(text=user_message_text)], role="user")
        
        should_retry_externally_from_adk = False # Bandera del callback de ADK para reintento externo
        
        try:
            events_processed_count = 0
            async for event in runner_adk.run_async(
                user_id=user_id_adk, session_id=session_id_adk, new_message=adk_message
            ):
                events_processed_count += 1
                logger.debug(f"🤖 Evento ADK #{events_processed_count} | Autor: {event.author} | Es Final: {event.is_final_response()} | Tipo de Evento: {type(event).__name__}")
                
                # --- Detección de señal de reintento externo desde el LLM callback ---
                # Se obtiene el estado de la sesión después de CADA evento para detectar la bandera
                current_session_state_adk = await session_service_adk.get_session(
                    app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk
                )
                if current_session_state_adk and current_session_state_adk.state.get('_should_retry_llm_call_externally'):
                    should_retry_externally_from_adk = True
                    # Capturamos el mensaje que el callback sugirió para el reintento
                    agent_final_response_text = current_session_state_adk.state.get('_external_retry_message', "Problema de servidor, reintentando...")
                    # Limpiar la bandera en el estado para el siguiente ciclo
                    current_session_state_adk.state['_should_retry_llm_call_externally'] = False 
                    logger.warning(f"⚠️ [Telegram_Loop] Señal de reintento externo detectada por el callback de ADK. ({agent_final_response_text})")
                    break # Salir del bucle de eventos para reintentar el run_async completo
                # --- Fin de detección de señal de reintento externo ---

                # Capturar la última respuesta textual del agente (puede ser intermedia o final)
                current_event_text = ""
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            text_content = part.text.strip()
                            if text_content:
                                current_event_text += text_content + " "
                                logger.debug(f"  -> Texto en evento: '{text_content}'")
                        
                        # Revisar si hay una solicitud de acción para el bot de Telegram (desde herramienta)
                        function_responses = event.get_function_responses()
                        if function_responses:
                            for fr in function_responses:
                                logger.info(f"🛠️ Herramienta llamada: {fr.name} | Respuesta: {fr.response.get('status', 'N/A')}")
                                if isinstance(fr.response, dict):
                                    if fr.response.get("action_request") == "SEND_PDF_MENU_TO_USER":
                                        action_to_perform_by_telegram_bot = "SEND_PDF_MENU_TO_USER"
                                        pdf_to_send = fr.response.get("pdf_file_name", MENU_PDF_FILENAME)
                                        message_before_pdf = fr.response.get("message_to_user_before_pdf")
                                        logger.info(f"📥 Acción: SEND_PDF_MENU_TO_USER solicitada. Archivo: {pdf_to_send}")
                                        if message_before_pdf:
                                            agent_final_response_text = message_before_pdf
                                        break # Salir del bucle de function_responses

                if event.is_final_response():
                    final_text_parts = []
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                final_text_parts.append(part.text.strip())
                    if final_text_parts:
                        agent_final_response_text = " ".join(final_text_parts).strip()
                    
                    if not agent_final_response_text and action_to_perform_by_telegram_bot:
                        agent_final_response_text = "Procesando su solicitud..." 
                    
                    logger.info(f"✅ Respuesta FINAL del agente ADK para {user_id_adk}: '{agent_final_response_text[:100]}...'") 
                    break # Salir del bucle de eventos al obtener la respuesta final del agente para este turno
            
            # --- Lógica de reintento del bucle while (después de que el bucle de eventos termina) ---
            if should_retry_externally_from_adk:
                telegram_retry_count += 1
                if telegram_retry_count < MAX_TELEGRAM_RETRIES:
                    backoff_delay = INITIAL_BACKOFF_SECONDS * (2 ** (telegram_retry_count - 1))
                    logger.info(f"⏳ [Telegram_Loop] Reintentando ADK run_async en {backoff_delay:.1f} segundos...")
                    await asyncio.sleep(backoff_delay)
                    continue # Volver al inicio del bucle while para reintentar run_async
                else:
                    logger.critical(f"🛑 [Telegram_Loop] Máximo de reintentos ({MAX_TELEGRAM_RETRIES}) alcanzado. Fallo crítico de ADK LLM.")
                    agent_final_response_text = "Lo siento, Angelo no puede procesar tu solicitud en este momento debido a un problema persistente con el servidor. Por favor, intenta de nuevo más tarde."
                    break # Salir del bucle while, se agotaron los reintentos
            else:
                break # Si no hay que reintentar, salir del bucle while (proceso exitoso o error no manejado)

        except Exception as e:
            logger.error(f"❌ Error durante el runner_adk.run_async (Intento {telegram_retry_count + 1}/{MAX_TELEGRAM_RETRIES}): {e}", exc_info=True)
            telegram_retry_count += 1
            if telegram_retry_count < MAX_TELEGRAM_RETRIES:
                backoff_delay = INITIAL_BACKOFF_SECONDS * (2 ** (telegram_retry_count - 1))
                logger.info(f"⏳ [Telegram_Loop] Error inesperado. Reintentando en {backoff_delay:.1f} segundos...")
                await asyncio.sleep(backoff_delay)
                continue # Volver al inicio del bucle while para reintentar run_async
            else:
                logger.critical(f"🛑 [Telegram_Loop] Máximo de reintentos ({MAX_TELEGRAM_RETRIES}) alcanzado. Fallo crítico.")
                agent_final_response_text = "Lo siento, Angelo no puede procesar tu solicitud en este momento debido a un problema persistente. Por favor, intenta de nuevo más tarde."
                break # Salir del bucle while, se agotaron los reintentos
    # --- Fin del bucle principal de reintentos ---

    # --- Lógica de envío de respuesta al usuario (fuera del bucle de reintentos) ---
    if agent_final_response_text and agent_final_response_text != "Lo siento, estoy teniendo algunos problemas para procesar tu solicitud en este momento.": # Asegurar que no sea el mensaje por defecto inicial
        await update.message.reply_text(agent_final_response_text)
        logger.info(f"📤 Bot respondió texto al chat {chat_id_telegram}: '{agent_final_response_text[:100]}...'")

    # Realizar la acción especial si fue solicitada (ej. enviar PDF)
    if action_to_perform_by_telegram_bot == "SEND_PDF_MENU_TO_USER":
        if os.path.exists(pdf_to_send):
            logger.info(f"📤 Enviando PDF '{pdf_to_send}' al chat {chat_id_telegram}")
            try:
                with open(pdf_to_send, 'rb') as pdf_file:
                    await context.bot.send_document(chat_id=chat_id_telegram, document=InputFile(pdf_file))
                logger.info(f"✅ PDF '{pdf_to_send}' enviado exitosamente.")
            except Exception as e_pdf:
                logger.error(f"❌ Error al enviar PDF '{pdf_to_send}': {e_pdf}", exc_info=True)
                await update.message.reply_text("Lo siento, tuve un problema al intentar enviarte el menú en PDF.")
        else:
            logger.error(f"❌ Archivo PDF del menú '{pdf_to_send}' no encontrado en el servidor.")
            await update.message.reply_text("Lo siento, no pude encontrar el archivo del menú para enviártelo.")
    
    # Si no hubo ninguna respuesta textual final del agente (o fue la de error por defecto inicial) 
    # Y no hubo ninguna acción especial solicitada, enviar una respuesta por defecto.
    elif not agent_final_response_text or agent_final_response_text == "Lo siento, estoy teniendo algunos problemas para procesar tu solicitud en este momento.":
         if not action_to_perform_by_telegram_bot:
            await update.message.reply_text("Parece que no tengo una respuesta para eso en este momento.")
            logger.info(f"⚠️ Bot envió respuesta por defecto (sin texto/acción ADK final).")


    final_session_state = await session_service_adk.get_session(app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk)
    if final_session_state:
        logger.info(f"📊 Estado final ADK ({session_id_adk}) | MainGoal: {final_session_state.state.get('current_main_goal', 'N/A')} | SubPhase: {final_session_state.state.get('processing_order_sub_phase', 'N/A')} | Pedido Pendiente: {final_session_state.state.get('_pending_order_check_result', 'No')}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje cuando el comando /start es ejecutado e inicializa la sesión ADK."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info(f"▶️ Comando /start recibido de user {user.id} en chat {chat_id}")
    
    # Asegurar/crear sesión ADK
    user_id_adk, session_id_adk = await get_or_create_adk_session(user.id, chat_id)
    
    # Forzar el primer mensaje "hola" al RootAgent para iniciar el flujo de CMA
    # Esto simula que el usuario dijo "hola" después de /start
    initial_simulated_message = "hola"
    adk_message = genai_types.Content(parts=[genai_types.Part(text=initial_simulated_message)], role="user")
    
    agent_greeting = "¡Hola! Soy Angelo de PizzeríaBot. ¿Cómo puedo ayudarte?" # Saludo por defecto si ADK falla
    try:
        # LOG AJUSTADO: Reducir verbosidad de eventos internos de /start
        logger.debug(f"Simulando mensaje '{initial_simulated_message}' para RootAgent vía /start...")
        async for event in runner_adk.run_async(
            user_id=user_id_adk, session_id=session_id_adk, new_message=adk_message
        ):
            if event.is_final_response() and event.content and event.content.parts and event.content.parts[0].text:
                agent_greeting = event.content.parts[0].text.strip()
                logger.info(f"✅ RootAgent respondió a /start para {user_id_adk}: '{agent_greeting[:100]}...'")
                break
    except Exception as e:
        logger.error(f"❌ Error en ADK durante /start para user {user_id_adk}: {e}", exc_info=True)
        
    await update.message.reply_html(agent_greeting)


def main() -> None:
    """Inicia el bot de Telegram."""
    if not TELEGRAM_BOT_TOKEN: # Doble chequeo
        print("El token de Telegram no está configurado. Saliendo.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Iniciando bot de Telegram con long polling...")
    application.run_polling(drop_pending_updates=True)
    
if __name__ == '__main__':
    main()