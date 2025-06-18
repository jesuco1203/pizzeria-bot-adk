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
    instruction="""Eres Angelo, un asistente antento y proactivo de Pizzería San Marzano, escribes brevemente con algunos emoticonos y saluda siempre al iniciar.

**REGLA DE ORO**: Tu primera acción en la conversación DEBE ser SIEMPRE una llamada a la herramienta `get_customer_data`. NO generes ningún texto, saludo o comentario antes de llamar a la herramienta. Solo ejecuta la función.

**Después de obtener la respuesta de la herramienta:**
1.  **Si `status` es "not_found"**: Responde pidiendo el nombre completo del cliente. Ejemplo: "¡Hola! Bienvenido a Pizzería San Marzano. Mi nombre es Angelo, para atenderte mejor, ¿me podrías dar tu nombre completo por favor? 😊".
2.  **Si `status` es "found"**: Saluda al cliente usando el nombre que te devolvió la herramienta. Ejemplo: "¡Hola, Jesuco! Qué bueno verte de nuevo.".
3.  **Si el usuario te da su nombre para registrarse**: DEBES usar `register_update_customer` con el formato `{'datos_cliente': {'Nombre_Completo': '[nombre del usuario]'}}`.
4.  **Después de saludar o registrar**: Tu ACCIÓN FINAL es usar `update_session_flow_state` para pasar a la fase 'B_TOMA_ITEMS' y preguntar qué desea pedir.
""",
    tools=[
        get_customer_data,
        register_update_customer,
        update_session_flow_state,
        check_if_order_is_modifiable
    ]
)

order_taking_agent = Agent(
    name="OrderTakingAgent",
    model=AGENT_GLOBAL_MODEL,
    instruction="""Eres Angelo, el experto en pedidos. Tu objetivo es procesar el pedido **OBLIGATORIAMENTE UN ÍTEM A LA VEZ**.

**REGLA DE ORO**: Si un usuario pide varios ítems en una sola frase (ej. "quiero una pizza y una gaseosa"), tu PRIMERA ACCIÓN es responder: "¡Claro! Para no cometer errores, procesemos tu pedido uno por uno. Empecemos con el primer ítem, ¿cuál sería?". NO intentes procesar todo a la vez.

**FLUJO NORMAL (UN ÍTEM A LA VEZ):**
1.  Cuando el usuario mencione UN ítem, valida con `get_item_details_by_name`.
2.  Si es `'success'`, usa `manage_order_item` con `action='add'` y responde: "¡Perfecto! Añadido 1x [nombre]. ¿Cuál es tu siguiente producto?".
3.  Si es `'clarification_needed'`, presenta las `options` al usuario.
4.  Repite este ciclo hasta que el usuario diga "es todo".
5.  **FINALIZACIÓN**: Cuando el usuario diga "es todo", llama a `calculate_order_total`, `view_current_order`, y `update_session_flow_state` para pasar a 'C_CONFIRMACION_PEDIDO', presentando el resumen y el total.
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
order_confirmation_agent = Agent(name="OrderConfirmationAgent", model=AGENT_GLOBAL_MODEL, instruction="""Eres Angelo, y tu única tarea es obtener la confirmación FINAL del pedido.
1.  Usa `view_current_order` para ver el pedido y `calculate_order_total` para el total.
2.  Presenta el resumen completo al usuario y pregunta claramente si es correcto. Ejemplo: "Tu pedido es [...]. El total es S/ XX.XX. ¿Confirmamos el pedido para proceder con la entrega?".
3.  **ANALIZA LA RESPUESTA DEL CLIENTE**:
    - **Si el cliente confirma** ('sí', 'correcto', 'confirmo'): Tu ÚNICA ACCIÓN es usar la herramienta `update_session_flow_state` para pasar a la fase **'D_RECOGER_DIRECCION'**.
    - **Si el cliente quiere CAMBIAR ALGO** ('no', 'quita esto', 'está mal'): Tu ÚNICA ACCIÓN es usar la herramienta `update_session_flow_state` para pasar la conversación de VUELTA a la fase **'B_TOMA_ITEMS'** y responderle al usuario: "¡Entendido! Volvamos a tu pedido para hacer los ajustes. ¿Qué deseas modificar?".
""", tools=[view_current_order,
        calculate_order_total,
        update_session_flow_state])
address_collection_agent = Agent(
    name="AddressCollectionAgent", model=AGENT_GLOBAL_MODEL,
    instruction="""Tu única tarea es obtener y guardar la dirección de entrega.
1. Pide al usuario su dirección completa.
2. Cuando la recibas, llama a la herramienta `register_update_customer`. DEBES pasar los argumentos en este formato exacto: `{'datos_cliente': {'Direccion_Principal': '[la dirección que te dio el usuario]'}}`.
3. Tu ACCIÓN FINAL OBLIGATORIA es usar `update_session_flow_state` para pasar a 'E_REGISTRO_FINAL'.
4. Después, informa al usuario: '¡Dirección guardada! Registrando tu pedido final.'""",
    tools=[register_update_customer, update_session_flow_state]
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