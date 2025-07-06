# telegram_pizzeria_bot.py
# Fecha: 6 de Julio, 2025
# VERSIÓN CORREGIDA PARA MANEJAR TRANSICIONES SILENCIOSAS DE ADK

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv, find_dotenv
import json

# Importar componentes ADK
from pizzeria_agents import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.adk.events import Event

# --- Configuración de Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('google_adk').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# --- Configuración del Bot y ADK ---
env_path = find_dotenv(usecwd=True)
if env_path:
    logger.info(f"Archivo .env encontrado en: {env_path}")
    load_dotenv(dotenv_path=env_path, verbose=True)
else:
    logger.info("Archivo .env NO encontrado.")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.critical("¡Error Crítico! TELEGRAM_BOT_TOKEN no encontrado.")
    exit()

APP_NAME_ADK = "PizzeriaChatBot_Telegram_v3"
session_service_adk = InMemorySessionService()
runner_adk = Runner(agent=root_agent, app_name=APP_NAME_ADK, session_service=session_service_adk)


async def get_or_create_adk_session(user_id_telegram: int):
    """Obtiene o crea una sesión ADK para un usuario de Telegram."""
    user_id_adk = str(user_id_telegram)
    session_id_adk = str(user_id_telegram) # Usamos el mismo ID para simplicidad

    current_session = await session_service_adk.get_session(
        app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk
    )
    if current_session is None:
        logger.info(f"No se encontró sesión para user {user_id_adk}. Creando una nueva...")
        initial_state = {
            '_session_user_id': user_id_adk,
            'processing_order_sub_phase': 'A_GESTION_CLIENTE',
        }
        await session_service_adk.create_session(
            app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk, state=initial_state
        )
        logger.info(f"Nueva sesión ADK creada para user {user_id_adk}. Estado inicial: {initial_state}")
    else:
        # Aseguramos que el estado y la fase inicial existan
        if not current_session.state:
            current_session.state = {}
        if 'processing_order_sub_phase' not in current_session.state:
            current_session.state['processing_order_sub_phase'] = 'A_GESTION_CLIENTE'
        current_session.state['_session_user_id'] = user_id_adk
        logger.info(f"Sesión ADK existente recuperada para user {user_id_adk}. Estado actual: {current_session.state}")

    return user_id_adk, session_id_adk


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja los mensajes de texto del usuario con una lógica de bucle para procesar
    transiciones de estado silenciosas dentro de un mismo turno de conversación.
    """
    if not update.message or not update.message.text:
        return

    user_id_telegram = update.effective_user.id
    user_message_text = update.message.text
    logger.info(f"💬 Mensaje del usuario {user_id_telegram}: '{user_message_text}'")

    user_id_adk, session_id_adk = await get_or_create_adk_session(user_id_telegram)

    # Preparamos el mensaje inicial del usuario para la primera iteración del bucle.
    adk_message_to_process = genai_types.Content(parts=[genai_types.Part(text=user_message_text)], role="user")
    final_response_text = None
    
    # ==============================================================================
    # INICIO DE LA LÓGICA DE SOLUCIÓN: BUCLE DE PROCESAMIENTO DE TURNOS
    # ==============================================================================
    
    max_loops = 5 # Para evitar bucles infinitos en caso de un bug de estado.
    current_loop = 0

    while current_loop < max_loops:
        current_loop += 1
        logger.info(f"🔄 Iniciando ciclo de procesamiento ADK #{current_loop} para el turno.")

        # Obtener el estado de la fase ANTES de ejecutar el runner.
        session_before = await session_service_adk.get_session(app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk)
        phase_before = session_before.state.get('processing_order_sub_phase')

        text_response_from_turn = ""

        try:
            # Ejecutar el runner de ADK. En la primera vuelta, usa el mensaje del usuario.
            # En las siguientes, será None, permitiendo que el agente en la nueva fase actúe.
            events_stream = runner_adk.run_async(
                user_id=user_id_adk, session_id=session_id_adk, new_message=adk_message_to_process
            )
            
            async for event in events_stream:
                if event.is_final_response() and event.content and event.content.parts:
                    if event.content.parts[0].text:
                        text_response_from_turn = event.content.parts[0].text.strip()
                        logger.info(f"✅ Texto de respuesta final detectado en ciclo #{current_loop}: '{text_response_from_turn[:100]}...'")
            
            # Después del primer ciclo, las siguientes iteraciones se basan en el estado, no en un nuevo mensaje.
            adk_message_to_process = None

            # Obtener el estado de la fase DESPUÉS de ejecutar el runner.
            session_after = await session_service_adk.get_session(app_name=APP_NAME_ADK, user_id=user_id_adk, session_id=session_id_adk)
            phase_after = session_after.state.get('processing_order_sub_phase')

            # Si se obtuvo una respuesta textual, la guardamos y salimos del bucle.
            if text_response_from_turn:
                final_response_text = text_response_from_turn
                logger.info("El ciclo generó una respuesta de texto. Finalizando bucle de turno.")
                break

            # Si no hubo respuesta de texto, PERO la fase cambió, significa que hubo una transición silenciosa.
            # Continuamos el bucle para permitir que el nuevo agente actúe.
            elif phase_before != phase_after:
                logger.info(f"Transición de fase silenciosa detectada de '{phase_before}' a '{phase_after}'. Continuando ciclo...")
                continue

            # Si no hubo respuesta y la fase no cambió, el turno realmente terminó. Salimos.
            else:
                logger.warning("El ciclo terminó sin respuesta de texto y sin cambio de fase. Finalizando bucle de turno.")
                break

        except Exception as e:
            logger.error(f"❌ Error excepcional durante el ciclo de procesamiento ADK: {e}", exc_info=True)
            final_response_text = "Lo siento, ocurrió un error interno. Por favor, intenta de nuevo."
            break
            
    # ==============================================================================
    # FIN DE LA LÓGICA DE SOLUCIÓN
    # ==============================================================================

    # Enviar la respuesta final al usuario si se generó alguna.
    if final_response_text:
        await update.message.reply_text(final_response_text)
        logger.info(f"📤 Bot respondió al chat {user_id_telegram}: '{final_response_text[:100]}...'")
    else:
        # Si después de todo el proceso no hay respuesta, enviar un mensaje genérico.
        await update.message.reply_text("Entendido. ¿Necesitas algo más?")
        logger.warning(f"⚠️ El flujo del agente terminó sin una respuesta textual explícita para el usuario '{user_id_telegram}'.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje cuando el comando /start es ejecutado."""
    user = update.effective_user
    await get_or_create_adk_session(user.id) # Aseguramos que la sesión se cree/recupere.
    await update.message.reply_html(
        f"¡Hola {user.mention_html()}! 👋 Soy Angelo, tu asistente virtual de la Pizzería San Marzano. ¿En qué puedo ayudarte hoy?"
    )

def main() -> None:
    """Inicia el bot de Telegram."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Iniciando bot de Telegram...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()