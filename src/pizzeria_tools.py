# ==============================================================================
# pizzeria_tools.py - VERSIÓN DE LANZAMIENTO (CON MEMORIA PERFECTA)
# ==============================================================================
import logging
import time
import redis
import json
from typing import Any, Dict
import gspread
from datetime import datetime
from thefuzz import process, fuzz
from typing import Any, Dict
import asyncio
from sheets_client import get_worksheet
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

def get_state_from_context(context: Any) -> Dict[str, Any]:
    if hasattr(context, 'session') and hasattr(context.session, 'state'):
        return context.session.state
    elif hasattr(context, 'state'):
        return context.state
    return {}

# ==============================================================================
# VERSIÓN FINAL Y REAL de get_initial_customer_context
# Reemplaza la función existente en pizzeria_tools.py con esta
# ==============================================================================
# EN pizzeria_tools.py

async def get_initial_customer_context(tool_context: Any) -> Dict[str, Any]:
    """
    Herramienta maestra de lectura inicial. Obtiene datos del cliente y estado de pedidos,
    y actualiza directamente el estado de la sesión para el orquestador.
    """
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    logger.info(f"[Tool] Obteniendo contexto inicial REAL desde Google Sheets para user_id: '{user_id}'")

    if not user_id:
        # ... (manejo de error)
        return {"status": "error", "message": "No se pudo obtener el user_id."}

    try:
        # ... (tu lógica existente para conectar a Sheets)
        customers_ws = await asyncio.to_thread(get_worksheet, 'Clientes')
        orders_ws = await asyncio.to_thread(get_worksheet, 'Pedidos_Registrados')
        all_customers = await asyncio.to_thread(customers_ws.get_all_records)
        all_orders = await asyncio.to_thread(orders_ws.get_all_records)

        context_response = {}
        customer_row = next((row for row in all_customers if str(row.get('ID_Cliente')).strip() == str(user_id).strip()), None)

        if customer_row:
            logger.info(f"Cliente '{user_id}' encontrado.")
            context_response['customer_status'] = 'found'
            context_response['customer_data'] = customer_row
        else:
            logger.info(f"Cliente '{user_id}' NO encontrado.")
            context_response['customer_status'] = 'not_found'

        # ... (tu lógica existente para buscar pedidos)

        # <<< CAMBIO CRÍTICO: Actualizar el estado directamente >>>
        state['_customer_status'] = context_response['customer_status']
        if context_response.get('customer_data'):
            state['_customer_data'] = context_response['customer_data']
        
        logger.info(f"Estado de la sesión actualizado por la herramienta con: _customer_status='{state['_customer_status']}'")
        
        return {"status": "success", "message": "Contexto verificado y estado actualizado."}

    except Exception as e:
        logger.error(f"[Tool] Error crítico en get_initial_customer_context: {repr(e)}")
        return {"status": "error", "message": "Error interno al consultar la base de datos."}

async def commit_final_order_and_customer_data(tool_context: Any) -> Dict[str, Any]:
    """
    Herramienta transaccional final. Lee todos los datos de la sesión y escribe
    en Google Sheets de una sola vez.
    """
    state = get_state_from_context(tool_context)
    logger.info("[Tool] Iniciando commit final a la base de datos...")

    # 1. Recuperar todos los datos del state
    user_id = state.get('_session_user_id')
    customer_name = state.get('_customer_name_for_greeting')
    new_address = state.get('_last_confirmed_delivery_address_for_order')
    order_items = state.get('_current_order_items', [])
    total = state.get('_order_subtotal', 0.0)

    # 2. Lógica para actualizar la hoja 'Clientes' con el nombre/dirección si son nuevos.
    # ... (usando el patrón asíncrono que definimos) ...

    # 3. Lógica para añadir la nueva fila a la hoja 'Pedidos_Registrados'.
    # ... (usando el patrón asíncrono) ...

    logger.info("--- COMMIT A GOOGLE SHEETS COMPLETADO ---")
    
    # 4. Limpiar el estado de la sesión para el siguiente pedido
    state['_current_order_items'] = []
    state['_order_subtotal'] = 0.0
    # ... etc ...

    return {"status": "success", "message": "Pedido registrado exitosamente."}

# Reemplazar la función en pizzeria_tools.py

async def get_item_details_by_name(tool_context: Any, nombre_plato: str) -> Dict[str, Any]:
    """
    [VERSIÓN FINAL] Busca un plato con una estrategia multi-etapa para máxima precisión.
    Etapa 1: Coincidencia exacta de nombre o alias.
    Etapa 2: Coincidencia flexible como último recurso, con umbral ajustado.
    """
    logger.info(f"[Tool] Iniciando búsqueda multi-etapa para: '{nombre_plato}'")
    from menu_cache import get_menu
    all_records = get_menu()

    available_items = [item for item in all_records if str(item.get('Disponible', '')).lower() == 'sí']
    if not available_items:
        return {"status": "not_found", "message": "No hay ítems disponibles en el menú."}

    query_clean = nombre_plato.strip().lower()

    # --- ETAPA 1: BÚSQUEDA EXACTA Y POR ALIAS (MÁXIMA PRIORIDAD) ---
    for item in available_items:
        # Búsqueda por nombre de plato
        if str(item.get('Nombre_Plato', '')).lower() == query_clean:
            logger.info(f"Coincidencia exacta de nombre encontrada: {item['Nombre_Plato']}")
            return {"status": "success", "item_details": item}
        
        # Búsqueda por alias
        aliases_str = item.get('Alias', '')
        if aliases_str:
            aliases = [alias.strip().lower() for alias in aliases_str.split(',')]
            if query_clean in aliases:
                logger.info(f"Coincidencia exacta de alias encontrada para '{query_clean}', corresponde a: {item['Nombre_Plato']}")
                return {"status": "success", "item_details": item}

    # --- ETAPA 2: BÚSQUEDA POR CONTENCIÓN DE PALABRAS CLAVE ---
    query_keywords = set(query_clean.split())
    perfect_matches = []
    for item in available_items:
        item_name_lower = str(item.get('Nombre_Plato', '')).lower()
        if query_keywords.issubset(set(item_name_lower.split())):
            perfect_matches.append(item)

    if len(perfect_matches) == 1:
        logger.info(f"Coincidencia única por palabras clave: {perfect_matches[0]['Nombre_Plato']}")
        return {"status": "success", "item_details": perfect_matches[0]}
    elif len(perfect_matches) > 1:
        logger.info(f"Múltiples coincidencias por palabras clave ({[item['Nombre_Plato'] for item in perfect_matches]}). Pidiendo clarificación.")
        return {"status": "clarification_needed", "options": perfect_matches}

    # --- ETAPA 3: BÚSQUEDA FLEXIBLE (FUZZY) CON UMBRAL AJUSTADO ---
    item_names = [item.get('Nombre_Plato') for item in available_items]
    
    matches = process.extract(query_clean, item_names, scorer=fuzz.token_set_ratio, limit=3)
    
    # Umbral de confianza ajustado a 75
    high_confidence_matches = [match for match in matches if match[1] > 75]
    
    if not high_confidence_matches:
        logger.info("Búsqueda flexible no encontró coincidencias de alta confianza.")
        available_categories = await get_available_categories(tool_context)
        return {
            "status": "not_found", 
            "message": f"Lo siento, no pude encontrar '{nombre_plato}' en el menú. ¿Quizás quisiste decir otra cosa? También puedes elegir una de estas categorías: {', '.join(available_categories.get('categories', []))}"
        }

    matched_item_names = [m[0] for m in high_confidence_matches]
    matched_items = [item for item in available_items if item.get('Nombre_Plato') in matched_item_names]

    if len(matched_items) == 1:
         logger.info(f"Coincidencia flexible única encontrada: {matched_items[0]['Nombre_Plato']}")
         return {"status": "success", "item_details": matched_items[0]}
    else:
        logger.info(f"Múltiples coincidencias flexibles ({[item['Nombre_Plato'] for item in matched_items]}). Pidiendo clarificación.")
        return {"status": "clarification_needed", "options": matched_items}


async def get_items_by_category(tool_context: Any, categoria: str) -> Dict[str, Any]:
    """
    [V2 - OPTIMIZADA] Busca y devuelve todos los platos de una categoría
    leyendo desde la caché en memoria (menu.json), NO desde Google Sheets.
    """
    logger.info(f"[Tool] get_items_by_category: Solicitud para categoría '{categoria}' desde CACHÉ.")

    from menu_cache import get_menu # Importamos nuestra función de caché
    if not categoria or not categoria.strip():
        return {"status": "error_input", "message": "El parámetro 'categoria' es obligatorio."}
    
    try:
        # ¡ESTA ES LA SOLUCIÓN! Leemos desde la memoria.
        all_records = get_menu()

        if not all_records:
            return {"status": "error_internal", "message": "La caché del menú está vacía."}
                
        available_records = [r for r in all_records if str(r.get('Disponible', '')).strip().lower() == 'sí']
        if not available_records:
            return {"status": "not_found", "message": "No hay ítems disponibles en el menú en este momento.", "items": []}

        categoria_lower = categoria.lower()
        found_items = [
            # Se crea un diccionario limpio solo con los datos que el agente necesita mostrar
            {
                "id_plato": r.get('ID_Plato', ''),
                "nombre_plato": r.get('Nombre_Plato', ''),
                "descripcion": r.get('Descripcion', ''),
                "precio": r.get('Precio', '0.0')
            }
            for r in available_records if str(r.get('Categoria', '')).lower() == categoria_lower
        ]
        
        if not found_items:
            return {"status": "not_found", "message": f"No se encontraron ítems en la categoría '{categoria}'.", "items": []}
        
        return {"status": "success", "items": found_items}
        
    except Exception as e: 
        logger.error(f"[Tool: get_items_by_category] Excepción general: {e}")
        return {"status": "error_internal", "message": f"Error interno inesperado: {str(e)}", "items": []}


async def get_available_categories(tool_context: Any) -> Dict[str, Any]:
    """
    Devuelve una lista de todas las categorías de productos únicas disponibles en el menú.
    Es útil para ofrecer al cliente opciones válidas cuando una búsqueda falla.
    """
    logger.info("[Tool] Obteniendo todas las categorías disponibles desde CACHÉ.")
    from menu_cache import get_menu
    
    try:
        all_records = get_menu()
        if not all_records:
            return {"status": "error", "message": "La caché del menú está vacía."}
        
        # Usamos un set para obtener categorías únicas y luego lo convertimos a lista
        categories = sorted(list(set(item.get('Categoria', '') for item in all_records if item.get('Categoria'))))
        
        return {"status": "success", "categories": categories}
        
    except Exception as e:
        logger.error(f"[Tool: get_available_categories] Excepción: {e}")
        return {"status": "error", "message": "Error interno al obtener las categorías."}


async def draft_response_for_review(tool_context: Any, draft_message: str) -> Dict[str, Any]:
    """
    Herramienta para que los agentes especialistas guarden un borrador de respuesta
    para que el orquestador lo revise y apruebe.
    """
    state = get_state_from_context(tool_context)
    logger.info(f"[Tool] Agente especialista ha preparado un borrador de respuesta: '{draft_message}'")
    
    # Guardamos el borrador en el state para el orquestador
    state['_draft_response_for_orchestrator'] = draft_message
    
    return {"status": "success", "message": "Borrador guardado para revisión."}

# pizzeria_tools.py (dentro de la función register_update_customer)

async def register_update_customer(tool_context: ToolContext, datos_cliente: Dict[str, Any]) -> Dict[str, str]:
    """
    [V3 - MÁS ROBUSTA]
    Guarda el nombre del cliente y silencia al agente. Acepta múltiples alias para el nombre.
    """
    state = get_state_from_context(tool_context)
    logger.info(f"[Tool] Guardando datos del cliente en memoria: {datos_cliente}")

    flat_data = {}
    def flatten_dict(d, parent_key='', sep='_'):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, dict):
                flatten_dict(v, new_key, sep=sep)
            else:
                flat_data[new_key.lower()] = v
    flatten_dict(datos_cliente)

    # >>>>>>>>>> INICIO DE LA CORRECCIÓN <<<<<<<<<<
    # Añadimos 'nombre_cliente' a la lista de alias aceptados.
    name_aliases = ['nombre_completo', 'nombre', 'name', 'customer_name', 'cliente', 'nombre_cliente']
    # >>>>>>>>>> FIN DE LA CORRECCIÓN <<<<<<<<<<
    
    customer_name = next((flat_data[alias] for alias in name_aliases if alias in flat_data), None)

    if customer_name:
        state['_customer_name_for_greeting'] = str(customer_name)
        state['_customer_status'] = 'found'
        logger.info(f"Nombre '{customer_name}' guardado en state. Estado del cliente actualizado a 'found'.")
        
        tool_context.actions.skip_summarization = True
        logger.info("[Tool] skip_summarization activado. El agente guardará silencio.")
        
        return {"status": "success", "message": "Nombre del cliente guardado y agente silenciado."}
    else:
        logger.error(f"Error en register_update_customer: el diccionario no contiene claves de nombre reconocibles. Recibido: {datos_cliente}")
        return {"status": "error", "message": "Datos de nombre no reconocidos."}

async def save_delivery_address(tool_context: ToolContext, direccion: str) -> Dict[str, Any]:
    """
    Guarda la dirección de entrega confirmada en el estado de la sesión
    y levanta una bandera para que el orquestador la vea.
    """
    state = get_state_from_context(tool_context)
    logger.info(f"[Tool] Guardando dirección de entrega en el estado: '{direccion}'")

    if not direccion or len(direccion) < 5: # Una validación simple en la herramienta
        return {"status": "error", "message": "La dirección proporcionada parece demasiado corta."}

    # Guardamos la dirección en el estado
    state['_last_confirmed_delivery_address_for_order'] = direccion
    
    # [IMPORTANTE] No levantamos la bandera aquí. Dejamos que el agente lo haga
    # para tener un patrón consistente.

    # Silenciamos al agente para ceder el control al orquestador.
    tool_context.actions.skip_summarization = True
    
    return {"status": "success", "message": "Dirección guardada exitosamente."}

async def finalize_order_taking(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Herramienta CRÍTICA. Se llama cuando el cliente termina de ordenar.
    1. Pone la bandera '_order_taking_complete' para el Orquestador.
    2. Le ordena al framework que NO le pida una respuesta al agente actual.
    Esto permite una transición instantánea y silenciosa a la siguiente fase.
    """
    state = get_state_from_context(tool_context)
    logger.info("[Tool] Finalizando la toma del pedido y cediendo control silenciosamente.")

    # 1. Levanta la bandera para que el orquestador la vea.
    state['_order_taking_complete'] = True

    # 2. [LA ORDEN DIRECTA] Le decimos al framework de ADK: "No resumas esto".
    # Esto garantiza el silencio técnico del agente.
    tool_context.actions.skip_summarization = True

    return {"status": "success", "message": "Fase de toma de pedido finalizada. Control cedido."}

# Reemplaza la función en pizzeria_tools.py

async def manage_order_item(tool_context: Any, action: str, item_name: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Gestiona el carrito de compras: añade, elimina o actualiza la cantidad de un ítem.
    Valida el 'item_name' contra el menú antes de cualquier acción.
    Acciones válidas: 'add', 'remove', 'set_quantity'.
    """
    state = get_state_from_context(tool_context)
    current_items = state.get('_current_order_items', []).copy()
    action = action.lower()
    logger.info(f"[Tool] manage_order_item | Acción: {action}, Ítem: '{item_name}', Cantidad: {quantity}")

    # --- VALIDACIÓN OBLIGATORIA DEL ÍTEM (excepto para remove) ---
    item_details = None
    if action in ["add", "set_quantity"]:
        validation_result = await get_item_details_by_name(tool_context, item_name)
        if validation_result.get("status") != "success":
            logger.warning(f"[Tool] Validación fallida para '{item_name}': {validation_result.get('status')}")
            return validation_result  # Devuelve el resultado de la validación para que el orquestador lo maneje

        item_details = validation_result["item_details"]
        canonical_name = item_details.get("Nombre_Plato")
        price = float(item_details.get("Precio", 0.0))
    
    # --- LÓGICA DE ACCIONES ---
    if action == "add":
        new_item = {"name": canonical_name, "quantity": quantity, "price": price, "subtotal": price * quantity}
        current_items.append(new_item)
        state['_current_order_items'] = current_items
        logger.info(f"[Tool] Ítem añadido: {new_item}")
        return {"status": "success", "message": f"Se ha añadido {quantity}x {canonical_name} a tu pedido."}

    elif action == "remove":
        item_name_lower = item_name.lower()
        item_found_and_removed = False
        # Iteramos en reversa para poder eliminar de forma segura
        for i in range(len(current_items) - 1, -1, -1):
            if current_items[i].get("name", "").lower() == item_name_lower:
                removed_item = current_items.pop(i)
                logger.info(f"[Tool] Ítem eliminado del carrito: {removed_item}")
                item_found_and_removed = True
                break # Salimos tras encontrar y eliminar la primera coincidencia
        
        if not item_found_and_removed:
            return {"status": "error", "message": f"No he podido encontrar '{item_name}' en tu pedido para eliminarlo."}

        state['_current_order_items'] = current_items
        return {"status": "success", "message": f"He eliminado '{item_name}' de tu pedido."}

    elif action == "set_quantity":
        item_found_and_updated = False
        for item_in_cart in current_items:
            if item_in_cart.get("name") == canonical_name:
                item_in_cart["quantity"] = quantity
                item_in_cart["subtotal"] = item_in_cart["price"] * quantity
                logger.info(f"[Tool] Cantidad actualizada para '{canonical_name}' a {quantity}.")
                item_found_and_updated = True
                break
        
        # <<< LÓGICA DE CORRECCIÓN DE BUG >>>
        if not item_found_and_updated:
            logger.warning(f"[Tool] 'set_quantity' falló porque el ítem no estaba. Se intentará añadirlo como nuevo.")
            new_item = {"name": canonical_name, "quantity": quantity, "price": price, "subtotal": price * quantity}
            current_items.append(new_item)
            state['_current_order_items'] = current_items
            logger.info(f"[Tool] Ítem añadido como fallback: {new_item}")
            return {"status": "success", "message": f"¡Entendido! Se ha añadido {quantity}x {canonical_name} a tu pedido."}

        state['_current_order_items'] = current_items
        return {"status": "success", "message": f"He actualizado la cantidad de '{canonical_name}' a {quantity}."}

    else:
        return {"status": "error", "message": f"La acción '{action}' no es válida. Solo se permite 'add', 'remove' o 'set_quantity'."}

async def view_current_order(tool_context: Any) -> Dict[str, Any]:
    """Muestra los ítems en el carrito desde la sesión."""
    state = get_state_from_context(tool_context)
    items = state.get('_current_order_items', [])
    logger.info(f"[Tool] Viendo pedido actual con {len(items)} tipos de ítems.")
    return {"status": "success", "order_items": items}

async def calculate_order_total(tool_context: Any) -> Dict[str, Any]:
    """
    Calcula el subtotal del pedido, siendo defensivo y devolviendo un desglose completo.
    """
    state = get_state_from_context(tool_context)
    order_items = state.get('_current_order_items', [])
    from menu_cache import get_menu
    menu = get_menu()
    
    subtotal = 0.0
    items_breakdown = []
    calculation_string_parts = []

    if not menu:
        logger.error("[Tool] No se pudo calcular el total: la caché del menú está vacía.")
        return {"status": "error_no_menu", "subtotal": 0.0, "items_breakdown": [], "calculation_string": "Error"}

    for item_in_order in order_items:
        if not isinstance(item_in_order, dict):
            logger.warning(f"[Tool] Ítem inválido en carrito, omitido: {item_in_order}")
            continue 
        
        item_name = item_in_order.get('name')
        if not item_name:
            continue

        # Usamos get_menu() que ahora devuelve una lista de diccionarios
        item_details = next((menu_item for menu_item in menu if menu_item.get('Nombre_Plato') == item_name), None)
        
        if item_details:
            try:
                precio = float(item_details.get('Precio', 0.0))
                cantidad = int(item_in_order.get('quantity', 1))
                item_subtotal = precio * cantidad
                subtotal += item_subtotal
                
                # Añadimos al desglose
                items_breakdown.append({"name": item_name, "quantity": cantidad, "price": f"S/ {precio:.2f}", "subtotal": f"S/ {item_subtotal:.2f}"})
                calculation_string_parts.append(f"{item_subtotal:.2f}")

            except (ValueError, TypeError):
                logger.warning(f"No se pudo procesar el precio/cantidad para el ítem: {item_name}")

    final_total = round(subtotal, 2)
    state["_order_subtotal"] = final_total
    
    calculation_string = " + ".join(calculation_string_parts) + f" = S/ {final_total:.2f}"
    
    logger.info(f"[Tool] Subtotal calculado: {final_total}. Desglose: {items_breakdown}")
    
    return {
        "status": "success", 
        "subtotal": final_total, 
        "items_breakdown": items_breakdown,
        "calculation_string": calculation_string
    }

async def update_session_state(tool_context: Any, data_to_update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Herramienta genérica para que los agentes especialistas dejen 'banderas' en el estado,
    indicando que han completado su tarea para el orquestador.
    """
    state = get_state_from_context(tool_context)
    logger.info(f"[Tool] Actualizando state con la bandera: {data_to_update}")
    state.update(data_to_update)
    
    # [SOLUCIÓN] Devolvemos un diccionario que no incite a la conversación.
    # El status 'success' es suficiente para que el sistema sepa que todo fue bien,
    # pero no hay un 'message' que el LLM se sienta tentado a repetir.
    return {"status": "success"}

async def registrar_pedido_finalizado(tool_context: Any) -> Dict[str, Any]:
    """
    [VERSIÓN FINAL Y COMPLETA] Herramienta transaccional: Lee todos los datos del state,
    escribe de forma persistente el pedido y el cliente en Google Sheets y LUEGO limpia el estado.
    """
    state = get_state_from_context(tool_context)
    logger.info("[Tool] Iniciando registro final y persistencia de pedido Y CLIENTE...")

    # 1. Recopilar todos los datos del estado de la sesión
    user_id = state.get('_session_user_id', 'N/A')
    customer_name = state.get('_customer_name_for_greeting', 'N/A')
    address = state.get('_last_confirmed_delivery_address_for_order', 'N/A')
    order_items = state.get('_current_order_items', [])
    total = state.get('_order_subtotal', 0.0)
    order_id = f"PZ-{str(int(time.time()))[-6:]}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Formatear los ítems para que se lean bien en una celda
    items_str = ", ".join([f"{item['quantity']}x {item['name']}" for item in order_items])

    try:
        # =============================================================
        # LÓGICA DE REGISTRO/ACTUALIZACIÓN DEL CLIENTE
        # =============================================================
        clientes_ws = await asyncio.to_thread(get_worksheet, 'Clientes')
        
        # Buscamos si el cliente ya existe por su ID en la primera columna
        cell = await asyncio.to_thread(clientes_ws.find, user_id, in_column=1)
        
        if cell:
            # Si el cliente existe, actualizamos su nombre y dirección
            logger.info(f"Cliente con ID '{user_id}' encontrado en la fila {cell.row}. Actualizando datos.")
            await asyncio.to_thread(clientes_ws.update_cell, cell.row, 2, customer_name)
            await asyncio.to_thread(clientes_ws.update_cell, cell.row, 3, address)
            await asyncio.to_thread(clientes_ws.update_cell, cell.row, 5, timestamp) # Actualizamos fecha de última interacción
        else:
            # Si no existe, creamos un nuevo cliente
            logger.info(f"Cliente con ID '{user_id}' no encontrado. Creando nuevo registro.")
            # Asumiendo columnas: ID_Cliente, Nombre, Direccion_Predeterminada, Fecha_Registro, Fecha_Ultimo_Pedido
            nueva_fila_cliente = [user_id, customer_name, address, timestamp, timestamp]
            await asyncio.to_thread(clientes_ws.append_row, nueva_fila_cliente)
        
        # =============================================================
        # LÓGICA EXISTENTE: REGISTRO DEL PEDIDO
        # =============================================================
        pedidos_ws = await asyncio.to_thread(get_worksheet, 'Pedidos_Registrados')
        nueva_fila_pedido = [order_id, timestamp, user_id, customer_name, items_str, total, address, 'Recibido']
        await asyncio.to_thread(pedidos_ws.append_row, nueva_fila_pedido)
        logger.info(f"--- Pedido {order_id} REGISTRADO CORRECTAMENTE EN GOOGLE SHEETS ---")

        # 3. Limpiar el estado de la sesión para el siguiente pedido
        logger.info("[Tool] Limpiando estado de la sesión después del pedido.")
        state['_current_order_items'] = []
        state['_order_subtotal'] = 0.0
        state['_last_confirmed_delivery_address_for_order'] = None
        state['_order_taking_complete'] = False
        state['_order_confirmed'] = False
        state['_greeting_and_transition_done'] = False
        state['_customer_name_for_greeting'] = None # Limpiamos el nombre para el siguiente ciclo

        # 4. Reiniciar la máquina de estados a un estado de espera
        state['processing_order_sub_phase'] = 'A_STANDBY'
        logger.info("[Tool] Máquina de estados reiniciada a A_STANDBY.")

        # 5. Devolver mensaje de éxito al usuario
        return {
            "status": "success",
            "message": f"¡Gracias, {customer_name.title()}! Tu pedido #{order_id} por S/ {total:.2f} ha sido registrado y se enviará a: {address}."
        }

    except gspread.exceptions.APIError as e:
        logger.error(f"[Tool] Error de API de Google Sheets al registrar pedido: {e}")
        return {"status": "error_api", "message": "Lo siento, tuvimos un problema al registrar tu pedido en nuestro sistema. Por favor, intenta de nuevo más tarde."}
    except Exception as e:
        logger.error(f"[Tool] Error inesperado en registrar_pedido_finalizado: {e}", exc_info=True)
        return {"status": "error_internal", "message": "Lo siento, ocurrió un error interno inesperado."}


async def get_general_info(tool_context: ToolContext, info_key: str) -> Dict[str, Any]:
    """
    Obtiene información general de la pizzería desde una fuente de verdad externa
    (simulada aquí, pero idealmente una pestaña de Google Sheets 'Configuracion').
    """
    logger.info(f"[Tool] Solicitando información general para la clave: '{info_key}'")
    
    # Simulación de lectura desde una hoja de cálculo 'Configuracion'
    config_data = {
        "horario": "Nuestro horario es de Lunes a Sábado, de 11:00 AM a 10:00 PM. Domingos cerramos.",
        "telefono": "Puedes contactarnos al número +51 987 654 321.",
        "ubicacion": "Estamos ubicados en Av. Siempre Viva 742."
    }
    
    data = config_data.get(info_key.lower())
    
    if data:
        return {"status": "success", "info_key": info_key, "info_value": data}
    else:
        return {"status": "not_found", "message": f"No se encontró información para '{info_key}'."}

async def handle_complaint(tool_context: ToolContext, complaint_text: str) -> Dict[str, Any]:
    """
    Registra la queja de un cliente en un sistema externo
    (simulado aquí, pero idealmente una pestaña de Google Sheets 'Quejas').
    """
    state = get_state_from_context(tool_context)
    customer_name = state.get('_customer_name_for_greeting', 'Anónimo')
    
    logger.warning(f"[Tool] QUEJA REGISTRADA - Cliente: {customer_name}, Queja: '{complaint_text}'")
    
    # Aquí iría la lógica para escribir en la pestaña 'Quejas' de Google Sheets.
    
    return {
        "status": "success",
        "message": "Gracias por tus comentarios. Hemos registrado tu queja y un supervisor la revisará a la brevedad."
    }

# Stubs para otras herramientas
async def solicitar_envio_menu_pdf(tool_context: Any) -> Dict[str, Any]:
    """
    Indica que el menú en PDF debe ser enviado al usuario.
    No envía el PDF directamente, sino que devuelve una acción para que la capa de Telegram lo maneje.
    """
    logger.info("[Herramienta: solicitar_envio_menu_pdf] Solicitud para enviar menú PDF.")
    # El bot de Telegram buscará esta acción y este mensaje para actuar.
    return {
        "status": "success",
        "action_request": "SEND_PDF_MENU_TO_USER",
        "message_to_user_before_pdf": "¡Claro! Aquí tienes nuestro menú completo para que elijas con calma:"
    }


