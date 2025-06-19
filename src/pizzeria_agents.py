# ==============================================================================
# pizzeria_agents.py - VERSIÓN FINAL Y VERIFICADA
# ==============================================================================
print("--- EJECUTANDO VERSIÓN FINAL Y VERIFICADA ---")

import os
import time
import asyncio
import logging
from typing import Any, Dict, Optional, AsyncGenerator

from dotenv import load_dotenv, find_dotenv

# Carga de credenciales al principio de todo
env_path = find_dotenv(usecwd=True)
if env_path: load_dotenv(dotenv_path=env_path, verbose=True)

# --- Importaciones de ADK (CORREGIDAS Y VERIFICADAS) ---
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from google.adk.models.llm_request import LlmRequest
from google.genai import types as genai_types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
# --- Importaciones del Proyecto ---
from pizzeria_tools import (
    get_state_from_context, get_customer_data, register_update_customer,
    manage_order_item, view_current_order, get_saved_addresses,
    registrar_pedido_finalizado, solicitar_envio_menu_pdf, update_session_flow_state,
    calculate_order_total, get_items_by_category, get_item_details_by_name, check_if_order_is_modifiable
)
from menu_cache import load_menu_from_json
# --- Configuración de Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('google_adk').setLevel(logging.WARNING)
AGENT_GLOBAL_MODEL = os.environ.get("ADK_MODEL_NAME", "gemini-2.0-flash")
load_menu_from_json()
# --- AGENTES ESPECIALISTAS (con tasks simples) ---

customer_management_agent = Agent(
    name="CustomerManagementAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""Eres Angelo, un asistente proactivo y muy amable de Pizzería San Marzano.

**FLUJO DE TRABAJO OBLIGATORIO:**

**PASO 1: IDENTIFICAR AL CLIENTE**
- Tu PRIMERA ACCIÓN siempre es llamar a la herramienta `get_customer_data` para saber si conoces al cliente.

**PASO 2: VERIFICAR PEDIDOS RECIENTES**
- Después de obtener los datos del cliente, tu SEGUNDA ACCIÓN OBLIGATORIA es llamar a `check_if_order_is_modifiable`. NO saludes todavía.

**PASO 3: SALUDO INTELIGENTE (BASADO EN LOS PASOS 1 Y 2)**
- **CASO A (Cliente Nuevo):** Si `get_customer_data` devolvió "not_found", saluda y pide su nombre. Ejemplo: "¡Hola! Bienvenido a Pizzería San Marzano. Mi nombre es Angelo, para atenderte mejor, ¿me podrías dar tu nombre completo por favor? 😊".
- **CASO B (Cliente Conocido, Pedido Modificable):** Si `get_customer_data` devolvió "found" Y `check_if_order_is_modifiable` devolvió "modifiable", salúdalo por su nombre y pregúntale por su pedido anterior. Ejemplo: "¡Hola de nuevo, [Nombre_Completo]! Qué gusto verte. Oye, veo que hiciste un pedido hace [minutes_ago] minutos. ¿Te gustaría modificarlo o prefieres empezar uno nuevo?".
- **CASO C (Cliente Conocido, Pedido en Reparto):** Si el status es "in_delivery", infórmale. Ejemplo: "¡Hola, [Nombre_Completo]! Tu último pedido ya está en reparto, ¡llegará pronto! ¿Te gustaría hacer un nuevo pedido?".
- **CASO D (Cliente Conocido, Sin Pedido Reciente):** Si el status es "not_recent" o "no_prior_orders", dale una bienvenida personal y normal. Ejemplo: "¡Hola de nuevo, [Nombre_Completo]! Qué bueno verte por aquí. ¿Qué te apetece pedir hoy? 🍕".

**PASO 4: ACCIONES FINALES**
- Si registras un nuevo cliente, usa `register_update_customer`.
- Tu ACCIÓN FINAL, después de toda la interacción, es siempre usar `update_session_flow_state` para pasar a la fase 'B_TOMA_ITEMS'.
""",
    tools=[
        get_customer_data,
        register_update_customer,
        update_session_flow_state,
        check_if_order_is_modifiable  # <-- AÑADIMOS LA NUEVA HERRAMIENTA
    ]
)

order_taking_agent = Agent(
    name="OrderTakingAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""Eres Angelo, el experto en pedidos. Tu objetivo es procesar el pedido de forma ordenada.

**FLUJO DE PROCESAMIENTO OBLIGATORIO:**

1.  **DETECTAR PEDIDOS MÚLTIPLES**: Si el usuario pide varios productos a la vez, tu PRIMERA RESPUESTA debe ser para informarle que los procesarás uno por uno. Ejemplo: "¡Claro! Veo que pediste varias cosas. Para no cometer errores, vamos a agregarlas una por una. Empecemos con [el primer ítem que mencionaste]...". Al mismo tiempo, debes guardar los otros ítems que mencionó en una lista en la memoria de sesión bajo la clave `_pending_order_items`.

2.  **PROCESAR ÍTEM ACTUAL**: Procesa el ítem actual (sea el primero de una lista o uno que pidió individualmente). Usa `get_item_details_by_name` para validarlo y `manage_order_item` para añadirlo. Si hay ambigüedad, pide clarificación.

3.  **REVISAR TAREAS PENDIENTES**: Después de añadir un ítem exitosamente, ANTES de preguntar "¿Deseas agregar algo más?", DEBES revisar la lista `_pending_order_items` en la memoria.
    - **Si la lista NO está vacía**: Saca el siguiente ítem de la lista, y pregunta por él. Ejemplo: "¡Perfecto! Añadida la Pizza Americana. Continuemos con la pizza hawaiana que mencionaste. ¿De qué tamaño la quieres?".
    - **Si la lista ESTÁ vacía**: Ahora sí, pregunta: "¿Deseas agregar algo más?".

4.  **FINALIZACIÓN**: Cuando el usuario diga "es todo" (y la lista `_pending_order_items` esté vacía), procede a llamar a `calculate_order_total`, `view_current_order`, y `update_session_flow_state` para pasar a la fase 'C_CONFIRMACION_PEDIDO'.
""",
    tools=[
        get_items_by_category, 
        get_item_details_by_name,
        manage_order_item, 
        view_current_order, 
        calculate_order_total, 
        update_session_flow_state
    ]
)

order_confirmation_agent = Agent(
    name="OrderConfirmationAgent", 
    model=AGENT_GLOBAL_MODEL, 
    instruction="""Eres Angelo, y tu única tarea es obtener la confirmación FINAL del pedido.
1.  Usa `view_current_order` para ver el pedido y `calculate_order_total` para el total.
2.  Presenta el resumen completo al usuario (con desglose de precios) y pregunta claramente si es correcto. Ejemplo: "Tu pedido es [...]. El total es S/ XX.XX. ¿Confirmamos el pedido para proceder con la entrega?".
3.  **ANALIZA LA RESPUESTA DEL CLIENTE CON MÁXIMA ATENCIÓN**:
    - **Si el cliente confirma** ('sí', 'correcto', 'confirmo', 'dale'): Tu ÚNICA ACCIÓN es usar la herramienta `update_session_flow_state` para pasar a la fase **'D_RECOGER_DIRECCION'**. NO respondas nada más, el siguiente agente se encargará.
    - **Si el cliente quiere CAMBIAR ALGO o NO CONFIRMA** ('no', 'quita esto', 'está mal', 'quiero agregar'): Tu ÚNICA ACCIÓN es usar la herramienta `update_session_flow_state` para pasar la conversación de VUELTA a la fase **'B_TOMA_ITEMS'** y responderle al usuario: "¡Entendido! Volvamos a tu pedido para hacer los ajustes. ¿Qué deseas modificar?".
""", 
    tools=[
        view_current_order,
        calculate_order_total,
        update_session_flow_state
    ]
)

address_collection_agent = Agent(
    name="AddressCollectionAgent", 
    model=AGENT_GLOBAL_MODEL,
    instruction="""Tu única tarea es obtener y confirmar la dirección de entrega. Eres muy minucioso.

**FLUJO DE TRABAJO OBLIGATORIO:**

1.  **VERIFICAR DIRECCIONES GUARDADAS**: Tu PRIMERA ACCIÓN es llamar a `get_saved_addresses`.
2.  **REACCIONAR AL RESULTADO**:
    - **Si encuentras direcciones guardadas**: Muéstralas al usuario como opciones numeradas. Ejemplo: "Veo que tienes estas direcciones guardadas: 1. [Dirección Principal], 2. [Dirección Secundaria]. ¿Deseas que lo enviemos a alguna de ellas o prefieres ingresar una nueva?".
    - **Si NO encuentras direcciones**: Pide al usuario su dirección completa, pidiendo que incluya calle, número y una referencia.
3.  **VALIDAR Y CONFIRMAR LA DIRECCIÓN NUEVA**:
    - Cuando el usuario te dé una dirección, revísala. Si parece inválida (muy corta, sin números, etc.), insiste amablemente: "Esa dirección no parece muy completa. Para asegurar que tu pizza llegue caliente, ¿podrías darme más detalles como el nombre de la calle y el número?".
    - Una vez que tengas una dirección que parezca válida, **confírmala explícitamente**. Ejemplo: "Perfecto, entonces la dirección de entrega será: [dirección que dio el usuario]. ¿Es correcto?".
4.  **GUARDAR Y AVANZAR**:
    - SOLO cuando el usuario confirme que la dirección es correcta, llama a la herramienta `register_update_customer` para guardarla.
    - Inmediatamente después, tu ACCIÓN FINAL es usar `update_session_flow_state` para pasar a la fase **'E_REGISTRO_FINAL'**. No digas nada más. El orquestador se encargará del siguiente paso.
""",
    tools=[
        get_saved_addresses,
        register_update_customer, 
        update_session_flow_state
    ]
)
# --- ROOT AGENT ORQUESTADOR ---
class RootOrchestratorAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}
    customer_management_agent: Agent
    order_taking_agent: Agent
    order_confirmation_agent: Agent
    address_collection_agent: Agent
    def __init__(self, cma: Agent, ota: Agent, oca: Agent, aca: Agent):
        super().__init__(name="RootOrchestrator_Final", sub_agents=[cma, ota, oca, aca], customer_management_agent=cma, order_taking_agent=ota, order_confirmation_agent=oca, address_collection_agent=aca)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = get_state_from_context(ctx)
        sub_phase = state.get('processing_order_sub_phase', 'A_GESTION_CLIENTE')
        logger.info(f"[{self.name}] INICIO TURNO. Enrutando a la fase: {sub_phase}")
        target_agent = None
        if sub_phase == 'A_GESTION_CLIENTE': target_agent = self.customer_management_agent
        elif sub_phase == 'B_TOMA_ITEMS': target_agent = self.order_taking_agent
        elif sub_phase == 'C_CONFIRMACION_PEDIDO': target_agent = self.order_confirmation_agent
        elif sub_phase == 'D_RECOGER_DIRECCION': target_agent = self.address_collection_agent
        elif sub_phase == 'E_REGISTRO_FINAL':
            resultado = await registrar_pedido_finalizado(tool_context=ctx)
            yield Event(author=self.name, content=genai_types.Content(parts=[genai_types.Part(text=resultado.get("message"))]))

            final_state_changes = {'processing_order_sub_phase': 'A_GESTION_CLIENTE'}

            yield Event(author=self.name, actions=EventActions(state_delta=final_state_changes))

            return
        else:
            state['processing_order_sub_phase'] = 'A_GESTION_CLIENTE'
            target_agent = self.customer_management_agent
        if target_agent:
            async for event in target_agent.run_async(ctx):
                yield event
        logger.info(f"[{self.name}] FIN TURNO.")

# --- INSTANCIACIÓN Y PRUEBA ---
root_agent = RootOrchestratorAgent(cma=customer_management_agent, ota=order_taking_agent, oca=order_confirmation_agent, aca=address_collection_agent)
if __name__ == '__main__':
    async def interactive_chat():
        logger.info("--- Iniciando Chat Interactivo (PRODUCCIÓN) ---")
        runner = Runner(agent=root_agent, app_name="PizzeriaChatBot", session_service=InMemorySessionService())
        USER_ID = "consola_prod"
        session_id = f"session_{int(time.time())}"
        await runner.session_service.create_session(
            app_name="PizzeriaChatBot", user_id=USER_ID, session_id=session_id,
            state={'processing_order_sub_phase': 'A_GESTION_CLIENTE', '_session_user_id': USER_ID}
        )
        while True:
            user_query = input("\nTú > ")
            if user_query.lower() in ["salir", "quit"]: break
            adk_message = genai_types.Content(parts=[genai_types.Part(text=user_query)], role="user")
            final_response = "..."
            async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=adk_message):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text.strip()
            print(f"Angelo > {final_response}")
    if not os.environ.get("GOOGLE_API_KEY"): raise ValueError("GOOGLE_API_KEY no configurada.")
    asyncio.run(interactive_chat())