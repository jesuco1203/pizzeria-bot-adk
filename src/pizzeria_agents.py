# ==============================================================================
# pizzeria_agents.py - VERSIÓN FINAL CON ARQUITECTURA PING-PONG UNIVERSAL
# ==============================================================================
print("--- EJECUTANDO VERSIÓN PING-PONG UNIVERSAL ---")

import os
import time
import asyncio
import logging
import json
from typing import Any, Dict, Optional, AsyncGenerator

from dotenv import load_dotenv, find_dotenv

# Carga de credenciales
env_path = find_dotenv(usecwd=True)
if env_path: load_dotenv(dotenv_path=env_path, verbose=True)

# --- Importaciones de ADK ---
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool


# --- Importaciones del Proyecto ---
from pizzeria_tools import (
    get_state_from_context, get_initial_customer_context,
    manage_order_item, view_current_order, save_delivery_address,
    registrar_pedido_finalizado, update_session_state, get_general_info, handle_complaint,
    calculate_order_total, get_items_by_category, get_item_details_by_name, draft_response_for_review,
    register_update_customer, finalize_order_taking, get_available_categories
)
from menu_cache import load_menu_from_json
import google.generativeai as genai
from google.api_core import retry
from google.genai import errors
from google.api_core import exceptions as core_exceptions
from pydantic import PrivateAttr
from pizzeria_callbacks import log_before_tool_call, log_after_tool_call, log_before_model_call, log_after_model_call


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__) # Logger global para tareas a nivel de módulo
logging.getLogger('google_adk').setLevel(logging.WARNING)

AGENT_GLOBAL_MODEL = os.environ.get("ADK_MODEL_NAME", "gemini-2.5-flash-lite-preview-06-17")
load_menu_from_json()

# ==============================================================================
# AGENTES ESPECIALISTAS SIMPLIFICADOS (VERSIÓN PING-PONG)
# ==============================================================================

customer_management_agent = Agent(
    name="CustomerManagementAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Recepcionista Experto y Eficiente 🤵

    **1. ACCIÓN INICIAL:**
    - Al recibir CUALQUIER input, debes llamar a `get_initial_customer_context`.

        SI EL CLIENTE ES NUEVO(`_customer_status: 'not_found'`):**
            - Tu única acción es preguntar por su nombre.Puedes decir algo como: "¡Hola! Bienvenido(a) a Pizzería San Marzano 😊. Para atenderte mejor, ¿me podrías dar tu nombre completo?"
            Analiza la respuesta, si no parece un nombre, insiste amablemente para que escriba su nombre, cuando detectes un nombre usa `register_update_customer` y usa la variable 'nombre' para guardar su nombre.
    
        EL CLIENTE YA EXISTE (`_customer_status: 'found'`):
            - Tu única acción es saludar al cliente por su nombre. Por ejemplo: "¡Hola, [Nombre del Cliente]! Qué bueno verte de nuevo en Pizzería San Marzano 😊, estas listo para pedir?🍕

    **2. ACCIÓN POST-REGISTRO:**
       - SIMULTÁNEAMENTE, debes llamar a la herramienta `yield_control_silently` (o la que creemos) para notificar al orquestador que has terminado.
    """,
    tools=[get_initial_customer_context, register_update_customer],
    before_model_callback=log_before_model_call, # <-- AÑADIR
    after_model_callback=log_after_model_call,   # <-- AÑADIR
    before_tool_callback=log_before_tool_call,
    after_tool_callback=log_after_tool_call
)

order_taking_agent = Agent(
    name="OrderTakingAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Asistente de Pedidos Amigable y Eficiente 🤖🍕

    **PROTOCOLO DE EJECUCIÓN ESTRICTO:**

    **1. PROCESAMIENTO DE ÍTEMS:**
    - Cuando el cliente mencione un ítem, usa `manage_order_item` para añadirlo.
    - Después de añadir un ítem, pregunta siempre: "¿Algo más?".

    **2. FINALIZACIÓN DEL PEDIDO (REGLA DE ORO):**
    - Si el cliente dice "eso es todo" o una frase similar, tu ÚNICA acción es llamar a la herramienta `finalize_order_taking`. No hagas nada más.
    """,
    tools=[
        manage_order_item,
        view_current_order,
        finalize_order_taking, # Esta es la herramienta refactorizada
        get_items_by_category,
        get_item_details_by_name,
        get_available_categories
    ],
    before_model_callback=log_before_model_call, # <-- AÑADIR
    after_model_callback=log_after_model_call,   # <-- AÑADIR
    before_tool_callback=log_before_tool_call,
    after_tool_callback=log_after_tool_call
)

order_confirmation_agent = Agent(
    name="OrderConfirmationAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Verificador de Pedidos Robótico 🤖

    **PROTOCOLO DE EJECUCIÓN:**

    **1. ACCIÓN INICIAL (Al ser activado):**
       - Llama a las herramientas `view_current_order` y `calculate_order_total` para obtener los datos frescos del pedido.
       - Usa la información para construir y mostrar un resumen claro del pedido al usuario.
       - Finaliza tu mensaje preguntando **exactamente**: "¿Es correcto tu pedido?"

    **2. MANEJO DE RESPUESTA DEL CLIENTE (En el siguiente turno):**
       - Si el cliente responde afirmativamente ('sí', 'es correcto', 'confirmo'), tu **ÚNICA** acción es llamar a la herramienta `update_session_state` con los argumentos `data_to_update={'_order_confirmed': True}`.
       - Si el cliente quiere modificar ('no', 'cambiar', 'quitar'), tu **ÚNICA** acción es llamar a `update_session_state` con `data_to_update={'_modification_requested': True}`.
       - **NO generes texto después de llamar a `update_session_state`**. Cede el control.
    """,
    # Asegúrate de que tenga las herramientas necesarias
    tools=[
        view_current_order,
        calculate_order_total,
        update_session_state,
        manage_order_item, # Para poder modificar
        get_items_by_category, # Para poder mostrar opciones
        get_item_details_by_name # Para buscar ítems al modificar
    ],
    before_model_callback=log_before_model_call, # <-- AÑADIR
    after_model_callback=log_after_model_call,   # <-- AÑADIR
    before_tool_callback=log_before_tool_call,
    after_tool_callback=log_after_tool_call
)

address_collection_agent = Agent(
    name="AddressCollectionAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Especialista en Logística 🤖

    **DIRECTIVA PRINCIPAL:** Tu única misión es obtener y validar la dirección de entrega del cliente.

    **PROTOCOLO DE EJECUCIÓN ESTRICTO:**

    **1. ESTADO INICIAL:**
    - Tu primera acción es preguntar por la dirección. Responde: "¿A qué dirección te gustaría que enviemos tu pedido?".

    **2. VALIDACIÓN DE RESPUESTA:**
    - Si la dirección que da el cliente es válida (contiene letras y números), tu ÚNICA acción es llamar a la herramienta `save_delivery_address` con esa dirección. No generes texto después.
    - Si no es válida, insiste amablemente para obtener una dirección real.
    """,
    tools=[save_delivery_address],
    before_model_callback=log_before_model_call, # <-- AÑADIR
    after_model_callback=log_after_model_call,   # <-- AÑADIR
    before_tool_callback=log_before_tool_call,
    after_tool_callback=log_after_tool_call
)

finalization_agent = Agent(
    name="FinalizationAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Registrador Final de Pedidos 🤖

    **DIRECTIVA ÚNICA:** Eres un agente automático que no interactúa con el cliente.
    Al ser activado, tu **ÚNICA** acción es llamar inmediatamente a la herramienta `registrar_pedido_finalizado`.
    Después de la llamada, proporciona al usuario el mensaje de éxito que te devuelve la herramienta.
    """,
    tools=[registrar_pedido_finalizado] # Solo necesita esta herramienta
)

intent_classifier_agent = Agent(
    name="IntentClassifierAgent",
    model=AGENT_GLOBAL_MODEL, # Podemos usar el modelo más rápido y económico
    instruction="""
    ## Tu Rol: Clasificador de Intenciones Robótico

    Tu única tarea es analizar la solicitud del usuario y responder con un ÚNICO objeto JSON válido y nada más. No incluyas "```json" ni nada que no sea el JSON.

    Las posibles intenciones son:
    - 'TAKE_ORDER': Si el usuario pide un ítem del menú (pizza, lasaña, bebida), quiere modificar su pedido, o responde directamente a una pregunta sobre un ítem.
    - 'FINALIZE_ORDER': Si el usuario indica que ha terminado de ordenar (ej. "eso es todo", "nada más").
    - 'CONFIRM_ORDER': Si el usuario confirma su pedido (ej. "sí, es correcto", "confirmo").
    - 'GIVE_ADDRESS': Si el usuario proporciona una dirección de entrega.
    - 'ASK_SCHEDULE': Si el usuario pregunta por el horario de atención.
    - 'MAKE_COMPLAINT': Si el usuario expresa una queja o está molesto.
    - 'GREETING': Si el usuario solo está saludando (ej. "hola", "buenas tardes").
    - 'CONTINUE_CONVERSATION': Si el usuario responde a una pregunta de forma general, pero no encaja en las otras categorías (ej. "si", "claro", "ok", "sip").
    - 'PROVIDE_NAME': Si la respuesta del usuario parece ser un nombre de persona.
    - 'UNKNOWN': Si la intención no encaja en ninguna de las anteriores.

    Ejemplos:
    - Usuario: "una piza americana" -> {"intent": "TAKE_ORDER"}
    - Usuario: "a qué hora cierran?" -> {"intent": "ASK_SCHEDULE"}
    - Usuario: "si confirmo" -> {"intent": "CONFIRM_ORDER"}
    - Usuario: "jesus chavez" -> {"intent": "PROVIDE_NAME"}
    - Usuario: "si amigo" -> {"intent": "CONTINUE_CONVERSATION"}

    **REGLA DE ORO: TU RESPUESTA DEBE SER ÚNICAMENTE EL JSON.**
    """,
    # ¡Este agente es tan simple que no necesita herramientas!
    tools=[]
)

general_inquiry_agent = Agent(
    name="GeneralInquiryAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""
    ## Tu Rol: Conserje de Información General y Quejas

    Tu única misión es responder preguntas sobre temas generales como horarios, ubicación, o registrar quejas.
    Usa la herramienta `get_general_info` si preguntan por el horario, teléfono o ubicación.
    Usa la herramienta `handle_complaint` si el cliente expresa una queja, un problema o está molesto.
    Responde de forma concisa y directa a la pregunta. No tienes acceso a la información del pedido.
    """,
    tools=[get_general_info, handle_complaint]
)
class RootOrchestratorAgent(BaseAgent):
    """
    [ARQUITECTURA v5.1 - PLAN B] Orquestador simplificado que sigue el flujo
    propuesto por el usuario. Las transiciones entre fases son explícitas y
    requieren confirmación del usuario, eliminando la complejidad y los bugs.
    """
    model_config = {"arbitrary_types_allowed": True}
    
    customer_management_agent: Agent
    order_taking_agent: Agent
    order_confirmation_agent: Agent
    address_collection_agent: Agent
    general_inquiry_agent: Agent
    finalization_agent: Agent # Añadir declaración
    intent_classifier_agent: Agent

    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._logger = logging.getLogger(self.name)

# En pizzeria_agents.py, DENTRO de la clase RootOrchestratorAgent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        [ARQUITECTURA v5.4 - VERSIÓN CONSULTOR EXTERNO]
        El orquestador es un director de flujo puro y limpio. No ejecuta lógica de negocio.
        """
        state = get_state_from_context(ctx)
        user_query = ctx.user_content.parts[0].text if ctx.user_content and ctx.user_content.parts else ""
        self._logger.info(f"--- INICIO TURNO ORQUESTADOR --- Input Usuario: '{user_query}'")

        # El orquestador ya no llama a get_initial_customer_context. Confía en sus especialistas.

        # Clasificación de intención (se mantiene)
        intent = "UNKNOWN"
        # ... (tu código de clasificación de intención no cambia)
        try:
            intent_response_str = ""
            async for event in self.intent_classifier_agent.run_async(ctx):
                if event.is_final_response() and event.content and event.content.parts:
                    cleaned_json_str = event.content.parts[0].text.strip().replace("```json", "").replace("```", "").strip()
                    intent_response_str = cleaned_json_str
            
            intent_data = json.loads(intent_response_str)
            intent = intent_data.get("intent", "UNKNOWN")
            self._logger.info(f"Intención clasificada: '{intent}'")
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            self._logger.warning(f"No se pudo decodificar la intención. Se asume 'UNKNOWN'. Respuesta: '{intent_response_str}'. Error: {e}")


        # Lógica de desvío (se mantiene)
        if intent in ['ASK_SCHEDULE', 'MAKE_COMPLAINT']:
            self._logger.info(f"Desviando a GeneralInquiryAgent por intención '{intent}'.")
            async for event in self.general_inquiry_agent.run_async(ctx):
                yield event
            return

        # Bucle proactivo de gestión de fases (con la corrección de 'A_STANDBY' que hicimos)
        while True:
            current_phase = state.get('processing_order_sub_phase', 'A_GESTION_CLIENTE')

            if current_phase == 'A_STANDBY':
                self._logger.info("Modo 'A_STANDBY' detectado. Reiniciando a 'A_GESTION_CLIENTE' para nueva conversación.")
                current_phase = 'A_GESTION_CLIENTE'
                state['processing_order_sub_phase'] = current_phase

            # Forzar regreso a toma de pedido (se mantiene)
            if intent == 'TAKE_ORDER' and current_phase in ['C_CONFIRMACION_PEDIDO', 'D_RECOGER_DIRECCION']:
                self._logger.info("El usuario quiere volver a pedir. Forzando fase a B_TOMA_ITEMS y limpiando TODAS las banderas de transición.")
                state['processing_order_sub_phase'] = 'B_TOMA_ITEMS'
                state.pop('_order_taking_complete', None)
                state.pop('_order_confirmed', None)
                state.pop('_modification_requested', None)
                state.pop('_last_confirmed_delivery_address_for_order', None)
                current_phase = 'B_TOMA_ITEMS'

            self._logger.info(f"--- CICLO ORQUESTADOR --- Delegando a la fase: {current_phase}")
            agent_for_phase = self._get_agent_for_phase(current_phase, intent)

            if not agent_for_phase:
                self._logger.error(f"Error: No se encontró un agente para la fase '{current_phase}'. Finalizando turno.")
                yield Event(author=self.name, content=genai_types.Content(parts=[genai_types.Part(text="Lo siento, me he perdido. ¿Podemos empezar de nuevo?")]))
                break

            async for event in agent_for_phase.run_async(ctx):
                yield event
            
            next_phase = self._determine_next_phase(state)

            if next_phase == current_phase:
                self._logger.info(f"La fase '{current_phase}' se mantiene. Finalizando turno del orquestador.")
                break
            else:
                self._logger.info(f"¡TRANSICIÓN DE FASE! De '{current_phase}' a '{next_phase}'.")
                transition_message = self._get_transition_message(state, current_phase, next_phase)
                state_update_delta = {'processing_order_sub_phase': next_phase}
                self._consume_transition_flags(state)
                yield Event(
                    author=self.name,
                    actions=EventActions(state_delta=state_update_delta),
                    content=genai_types.Content(parts=[genai_types.Part(text=transition_message)]) if transition_message else None
                )
                current_phase = next_phase
    
    def _determine_next_phase(self, state: Dict[str, Any]) -> str:
        """Determina la fase siguiente basándose en las banderas del estado."""
        current_phase = state.get('processing_order_sub_phase')
        
        if current_phase == 'A_GESTION_CLIENTE' and state.get('_customer_status') == 'found':
            return 'B_TOMA_ITEMS'
        if current_phase == 'B_TOMA_ITEMS' and state.get('_order_taking_complete'):
            return 'C_CONFIRMACION_PEDIDO'
        if current_phase == 'C_CONFIRMACION_PEDIDO':
            if state.get('_order_confirmed'):
                return 'D_RECOGER_DIRECCION'
            if state.get('_modification_requested'):
                return 'B_TOMA_ITEMS' # Vuelve a tomar el pedido
        if current_phase == 'D_RECOGER_DIRECCION' and state.get('_last_confirmed_delivery_address_for_order'):
            return 'E_FINALIZAR_PEDIDO'
            
        return current_phase # Si no se cumple ninguna condición, la fase no cambia

    def _consume_transition_flags(self, state: Dict[str, Any]):
        """Limpia las banderas de transición después de usarlas para evitar bucles."""
        state.pop('_order_taking_complete', None)
        state.pop('_order_confirmed', None)
        state.pop('_modification_requested', None)

    def _get_transition_message(self, state: Dict[str, Any], from_phase: str, to_phase: str) -> Optional[str]:
        """Genera un mensaje amigable para el usuario durante las transiciones de fase."""
        if from_phase == 'A_GESTION_CLIENTE' and to_phase == 'B_TOMA_ITEMS':
            customer_name = state.get('_customer_name_for_greeting', 'Cliente')
            return f"¡Excelente, {customer_name.title()}! Ya estás registrado. Ahora, dime, ¿qué te gustaría pedir? 🍕"

        if from_phase == 'B_TOMA_ITEMS' and to_phase == 'C_CONFIRMACION_PEDIDO':
            return "¡Perfecto! Déjame preparar el resumen de tu pedido para que lo revises."
        
        if from_phase == 'C_CONFIRMACION_PEDIDO' and to_phase == 'D_RECOGER_DIRECCION':
            return "¡Pedido confirmado! 👍 Para terminar, ¿a qué dirección lo enviamos?"
            
        return None # Otras transiciones pueden ser silenciosas
                        

    def _determine_next_phase(self, state: Dict[str, Any]) -> str:
            """Determina la fase siguiente basándose en las banderas del estado."""
            current_phase = state.get('processing_order_sub_phase')
            
            if current_phase == 'A_GESTION_CLIENTE' and state.get('_customer_status') == 'found':
                return 'B_TOMA_ITEMS'
            # ESTA ES LA TRANSICIÓN CLAVE QUE ESTÁ FALLANDO
            if current_phase == 'B_TOMA_ITEMS' and state.get('_order_taking_complete'):
                return 'C_CONFIRMACION_PEDIDO'
            if current_phase == 'C_CONFIRMACION_PEDIDO':
                if state.get('_order_confirmed'):
                    return 'D_RECOGER_DIRECCION'
                if state.get('_modification_requested'):
                    return 'B_TOMA_ITEMS' # Vuelve a tomar el pedido si se pide modificar
            if current_phase == 'D_RECOGER_DIRECCION' and state.get('_last_confirmed_delivery_address_for_order'):
                return 'E_FINALIZAR_PEDIDO'
                
            return current_phase # Si no se cumple ninguna condición, la fase no cambia

    def _consume_transition_flags(self, state: Dict[str, Any]):
        """Limpia las banderas de transición después de usarlas para evitar bucles infinitos."""
        state.pop('_order_taking_complete', None)
        state.pop('_order_confirmed', None)
        state.pop('_modification_requested', None)


    def _get_agent_for_phase(self, phase: str, intent: str) -> Optional[BaseAgent]:
        if phase == 'A_GESTION_CLIENTE': return self.customer_management_agent
        if phase == 'B_TOMA_ITEMS': return self.order_taking_agent
        if phase == 'C_CONFIRMACION_PEDIDO': return self.order_confirmation_agent
        if phase == 'D_RECOGER_DIRECCION': return self.address_collection_agent
        if phase == 'E_FINALIZAR_PEDIDO': return self.finalization_agent
        return None

    # Dentro de la clase RootOrchestratorAgent en pizzeria_agents.py

    def _get_transition_message(self, state: Dict[str, Any], current_phase: str, next_phase: str) -> Optional[str]:
        """Genera un mensaje amigable para el usuario durante las transiciones de fase."""
        
        # Transición de A -> B (Después de registrar el nombre)
        if current_phase == 'A_GESTION_CLIENTE' and next_phase == 'B_TOMA_ITEMS':
            customer_name = state.get('_customer_name_for_greeting', 'Cliente')
            return f"¡Hola {customer_name.title()}, qué bueno verte! 😊 ¿Qué te gustaría ordenar hoy?"

        # Transición de B -> C (Después de tomar el pedido)
        if current_phase == 'B_TOMA_ITEMS' and next_phase == 'C_CONFIRMACION_PEDIDO':
            return "¡Perfecto! Déjame preparar el resumen de tu pedido..."
        
        # Transición de C -> D (Después de confirmar el pedido)
        if current_phase == 'C_CONFIRMACION_PEDIDO' and next_phase == 'D_RECOGER_DIRECCION':
            return "¡Pedido confirmado! Para terminar, ¿a qué dirección lo enviamos?"
            
        return None # No hay mensaje para otras transiciones

cma = customer_management_agent
ota = order_taking_agent
oca = order_confirmation_agent
aca = address_collection_agent
gia = general_inquiry_agent
fa = finalization_agent # <--- Nuevo
ica = intent_classifier_agent

root_agent = RootOrchestratorAgent(
    # Argumentos requeridos por BaseAgent
    name="RootOrchestrator_Robust",
    sub_agents=[cma, ota, oca, aca, fa, ica, gia],
    customer_management_agent=cma,
    order_taking_agent=ota,
    order_confirmation_agent=oca,
    address_collection_agent=aca,
    finalization_agent=fa,
    general_inquiry_agent=gia,  # <--- Añadir el nuevo agente
    intent_classifier_agent=ica
)

if __name__ == '__main__':
    async def interactive_chat():
        # --- CONFIGURACIÓN DE LOGGING CENTRALIZADA ---
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s'
        )
        logging.getLogger('google_adk').setLevel(logging.WARNING)
        main_logger = logging.getLogger(__name__)

        main_logger.info("--- Iniciando Chat Interactivo (PRODUCCIÓN) ---")
        
        runner = Runner(agent=root_agent, app_name="PizzeriaChatBot", session_service=InMemorySessionService())
        USER_ID = "consola_prod"
        session_id = f"session_{int(time.time())}"
        
        # ======================= INICIO DE LA CORRECCIÓN =======================

        # 1. HEMOS DESCOMENTADO EL BLOQUE NORMAL
        # Esto crea una sesión que empieza en la fase 'A_GESTION_CLIENTE'.
        main_logger.info("--- MODO PRODUCCIÓN: Iniciando en Fase A ---")
        await runner.session_service.create_session(
            app_name="PizzeriaChatBot", user_id=USER_ID, session_id=session_id,
            state={'processing_order_sub_phase': 'A_GESTION_CLIENTE', '_session_user_id': USER_ID}
        )
        
        # 2. HEMOS COMENTADO O ELIMINADO EL BLOQUE DE DEPURACIÓN
        """
        # [MODIFICACIÓN PARA DEPURACIÓN] - Forzamos el inicio en Fase B
        main_logger.info("--- MODO DEPURACIÓN: OMITIENDO FASE A ---")
        initial_state_for_debug = {
            'processing_order_sub_phase': 'B_TOMA_ITEMS',      # <--- Empezamos aquí
            '_session_user_id': USER_ID,
            '_customer_status': 'found',                      # <--- Simulamos cliente encontrado
            '_customer_name_for_greeting': 'Cliente de Prueba' # <--- Usamos un nombre de prueba
        }

        await runner.session_service.create_session(
            app_name="PizzeriaChatBot", 
            user_id=USER_ID, 
            session_id=session_id,
            state=initial_state_for_debug  # <--- Usamos el nuevo estado inicial
        )
        """
        # ======================== FIN DE LA CORRECCIÓN =========================

        while True:
            try:
                user_query = input("\nTú > ")
                if user_query.lower() in ["salir", "quit"]: break
                if not user_query: continue
                
                adk_message = genai_types.Content(parts=[genai_types.Part(text=user_query)], role="user")
                
                # --- INICIO: BUCLE DE REINTENTOS A NIVEL DE APLICACIÓN ---
                max_retries = 3
                wait_time = 2.0  # Empezar con 2 segundos de espera
                
                for attempt in range(max_retries):
                    try:
                        final_response = None
                        events_stream = runner.run_async(user_id=USER_ID, session_id=session_id, new_message=adk_message)
                        
                        async for event in events_stream:
                            if event.is_final_response() and event.content and event.content.parts:
                                if event.content.parts[0].text:
                                    final_response = event.content.parts[0].text.strip()

                        if final_response:
                            print(f"Angelo > {final_response}")
                        
                        break

                    except (core_exceptions.ServiceUnavailable, core_exceptions.ResourceExhausted, errors.ServerError) as e:
                        main_logger.warning(f"Error transitorio de la API (Intento {attempt + 1}/{max_retries}): {e}")
                        if attempt + 1 < max_retries:
                            main_logger.info(f"Reintentando en {wait_time} segundos...")
                            await asyncio.sleep(wait_time)
                            wait_time *= 2
                        else:
                            main_logger.error("Se alcanzó el número máximo de reintentos. Fallando.")
                            print("Angelo > Lo siento, estoy teniendo problemas para conectarme con mis sistemas. Por favor, inténtalo de nuevo en unos momentos.")
                            break
                # --- FIN: BUCLE DE REINTENTOS ---

            except KeyboardInterrupt:
                print("\nChat finalizado.")
                break
            except Exception as e:
                main_logger.error(f"Error inesperado en el chat interactivo: {e}", exc_info=True)
                print("Angelo > Ups, ocurrió un error inesperado. Vamos a intentarlo de nuevo.")

    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("La variable de entorno GOOGLE_API_KEY no está configurada.")
        
    asyncio.run(interactive_chat())