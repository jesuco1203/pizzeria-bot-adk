# ==============================================================================
# pizzeria_tools.py - VERSIÓN DE LANZAMIENTO (CON MEMORIA PERFECTA)
# ==============================================================================
import logging
import time
from typing import Any, Dict
import gspread
from datetime import datetime
from thefuzz import process, fuzz


import asyncio
from sheets_client import get_worksheet

logger = logging.getLogger(__name__)

def get_state_from_context(context: Any) -> Dict[str, Any]:
    """Devuelve el diccionario de estado de forma segura."""
    if hasattr(context, 'session') and hasattr(context.session, 'state'):
        return context.session.state
    elif hasattr(context, 'state'):
        return context.state
    return {}

async def get_customer_data(tool_context: Any) -> dict:
    """Busca datos de un cliente en la hoja 'Clientes' usando el ID de la sesión."""
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    logger.info(f"[Tool] Buscando cliente con user_id: '{user_id}'")
    if not user_id:
        return {"status": "error", "message": "ID de usuario no encontrado en sesión."}

    try:
        # <<< LÓGICA DE GOOGLE SHEETS INTEGRADA >>>
        customers_ws = await asyncio.to_thread(get_worksheet, 'Clientes')
        if not customers_ws:
            return {"status": "error_internal", "message": "No se pudo acceder a la BD de clientes."}
        
        all_data = await asyncio.to_thread(customers_ws.get_all_records)
        customer_row = next((row for row in all_data if str(row.get('ID_Cliente')) == str(user_id)), None)
        
        if customer_row:
            nombre_completo = customer_row.get('Nombre_Completo', '')
            state['_customer_name_for_greeting'] = nombre_completo
            logger.info(f"[Tool] Cliente encontrado: {nombre_completo}")
            return {"status": "found", "data": customer_row}
        else:
            logger.info(f"[Tool] Cliente {user_id} no encontrado.")
            return {"status": "not_found"}
            
    except Exception as e:
        logger.error(f"[Tool] Error crítico al buscar en Sheets: {repr(e)}")
        return {"status": "error_internal"}

# NUEVA HERRAMIENTA (reemplazará a get_customer_data y check_if_order_is_modifiable)

async def get_initial_customer_context(tool_context: Any) -> Dict[str, Any]:
    """
    Herramienta maestra de lectura inicial. Obtiene datos del cliente y verifica si hay
    un pedido reciente modificable en una sola llamada a la BD.
    """
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    logger.info(f"[Tool] Obteniendo contexto inicial para user_id: '{user_id}'")
    
    # Lógica para leer la hoja de Clientes y la de Pedidos_Registrados
    # ... (implementaremos esta lógica combinada) ...

    # Ejemplo del diccionario que devolverá:
    initial_context = {
        "status": "found", # o "not_found"
        "customer_data": {
            "Nombre_Completo": "Javichon Picholon",
            "Direccion_Principal": "jr. chapalete 343 hyo tmabo"
        },
        "modifiable_order": { # Esta clave solo existirá si hay un pedido modificable
            "order_id": "PZ-310889",
            "items": "[...]",
            "minutes_ago": 3
        }
    }
    
    # Esta herramienta escribirá toda esta información en el state para que los agentes la usen.
    state['initial_context_loaded'] = True
    state['customer_name'] = initial_context.get("customer_data", {}).get("Nombre_Completo")
    # etc.

    return initial_context

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
    Busca un plato con una estrategia de búsqueda multi-etapa para máxima precisión.
    Etapa 1: Coincidencia exacta de nombre o alias.
    Etapa 2: Coincidencia de todas las palabras clave.
    Etapa 3: Coincidencia flexible como último recurso.
    """
    logger.info(f"[Tool] Iniciando búsqueda multi-etapa para: '{nombre_plato}'")
    from menu_cache import get_menu
    all_records = get_menu()

    available_items = [item for item in all_records if str(item.get('Disponible', '')).lower() == 'sí']
    if not available_items:
        return {"status": "not_found", "message": "No hay ítems disponibles en el menú."}

    query_clean = nombre_plato.strip().lower()

    # --- ETAPA 1: BÚSQUEDA EXACTA (MÁXIMA PRIORIDAD) ---
    for item in available_items:
        if str(item.get('Nombre_Plato', '')).lower() == query_clean:
            logger.info(f"Coincidencia exacta encontrada: {item['Nombre_Plato']}")
            return {"status": "success", "item_details": item}
        aliases = [alias.strip().lower() for alias in str(item.get('Alias', '')).split(',')]
        if query_clean in aliases:
            logger.info(f"Coincidencia exacta de alias encontrada: {item['Nombre_Plato']}")
            return {"status": "success", "item_details": item}

    # --- ETAPA 2: BÚSQUEDA POR CONTENCIÓN DE PALABRAS CLAVE ---
    query_keywords = set(query_clean.split())
    perfect_matches = []
    for item in available_items:
        item_name_lower = item.get('Nombre_Plato', '').lower()
        # Si todas las palabras de la búsqueda están en el nombre del ítem
        if query_keywords.issubset(set(item_name_lower.split())):
            perfect_matches.append(item)

    if len(perfect_matches) == 1:
        logger.info(f"Coincidencia única por palabras clave: {perfect_matches[0]['Nombre_Plato']}")
        return {"status": "success", "item_details": perfect_matches[0]}
    elif len(perfect_matches) > 1:
        logger.info("Múltiples coincidencias por palabras clave. Pidiendo clarificación.")
        return {"status": "clarification_needed", "options": perfect_matches}

    # --- ETAPA 3: BÚSQUEDA FLEXIBLE (FUZZY) COMO ÚLTIMO RECURSO ---
    # (El código que teníamos antes, ahora como fallback)
    item_names = [item.get('Nombre_Plato') for item in available_items]
    matches = process.extract(query_clean, item_names, scorer=fuzz.token_set_ratio, limit=3)
    high_confidence_matches = [match for match in matches if match[1] > 85]

    if not high_confidence_matches:
        logger.info("Búsqueda flexible no encontró coincidencias.")
        return {"status": "not_found", "message": f"No pude encontrar '{nombre_plato}' en el menú."}

    matched_items = [item for item in available_items if item.get('Nombre_Plato') in [m[0] for m in high_confidence_matches]]

    if len(matched_items) == 1:
         return {"status": "success", "item_details": matched_items[0]}
    else:
        return {"status": "clarification_needed", "options": matched_items}

async def get_items_by_category(tool_context: Any, categoria: str) -> Dict[str, Any]:
    """
    Busca y devuelve todos los platos disponibles de una categoría específica del menú.
    Args:
        categoria (str): La categoría de platos a buscar (ej: "Pizzas", "Bebidas").
    Returns:
        Un diccionario con status y una lista de ítems o un mensaje de error.
    """
    logger.info(f"[Tool] get_items_by_category: Solicitud para categoría: '{categoria}'")
    if not categoria or not categoria.strip():
        return {"status": "error_input", "message": "El parámetro 'categoria' es obligatorio."}
    
    try:
        menu_sheet = await asyncio.to_thread(get_worksheet, 'Menú')
        if menu_sheet is None:
            return {"status": "error_internal", "message": "No se pudo conectar a la base de datos del menú."}
        
        all_records = await asyncio.to_thread(menu_sheet.get_all_records)
        
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

# En pizzeria_tools.py

async def register_update_customer(tool_context: Any, datos_cliente: Dict[str, Any]) -> Dict[str, str]:
    """
    Registra un nuevo cliente o actualiza sus datos. Es flexible con las claves de entrada
    y asegura que los datos se guarden tanto en la BD como en la memoria de sesión.
    """
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    if not user_id: return {"status": "error", "message": "Falta id_cliente en sesión."}
    
    inner_datos = datos_cliente.get('datos_cliente', datos_cliente)
    logger.info(f"[Tool] Registrando/Actualizando datos para '{user_id}': {inner_datos}")

    # --- LÓGICA DE ROBUSTEZ: Encontrar los datos sin importar la clave exacta ---
    datos_para_sheets = {}
    
    # Mapeo de posibles claves a la clave oficial de la base de datos
    key_mapping = {
        'Nombre_Completo': ['Nombre_Completo', 'nombre_completo', 'nombre'],
        'Direccion_Principal': ['Direccion_Principal', 'direccion_principal', 'direccion', 'dirección']
    }

    for official_key, possible_keys in key_mapping.items():
        for key in possible_keys:
            if key in inner_datos:
                datos_para_sheets[official_key] = inner_datos[key]
                break
    
    if not datos_para_sheets:
        logger.warning(f"[Tool] No se encontraron datos válidos (Nombre_Completo, Direccion_Principal) en la entrada: {inner_datos}")
        return {"status": "error", "message": "No se proporcionaron datos válidos para guardar."}
    # -------------------------------------------------------------------------
    
    try:
        customers_ws = await asyncio.to_thread(get_worksheet, 'Clientes')
        if not customers_ws: return {"status": "error_internal", "message": "No se pudo acceder a la BD de clientes."}
        
        headers = await asyncio.to_thread(customers_ws.row_values, 1)
        cell = None
        try:
            id_col = headers.index('ID_Cliente') + 1
            cell = await asyncio.to_thread(customers_ws.find, str(user_id), in_column=id_col)
        except (gspread.exceptions.CellNotFound, ValueError):
            cell = None

        if cell: # El cliente existe, actualizamos
            logger.info(f"Cliente {user_id} encontrado en fila {cell.row}. Actualizando datos: {datos_para_sheets}")
            for key, value in datos_para_sheets.items():
                if key in headers:
                    col_index = headers.index(key) + 1
                    await asyncio.to_thread(customers_ws.update_cell, cell.row, col_index, str(value))
                    logger.info(f"  -> Celda '{key}' actualizada.")
                else:
                    logger.warning(f"  -> La columna '{key}' no se encontró en los encabezados de Google Sheets. No se pudo actualizar.")
        else: # El cliente no existe, creamos
            logger.info(f"Cliente {user_id} no encontrado. Creando nueva fila con datos: {datos_para_sheets}")
            new_row = [''] * len(headers)
            new_row[headers.index('ID_Cliente')] = str(user_id)
            for key, value in datos_para_sheets.items():
                if key in headers:
                    new_row[headers.index(key)] = str(value)
            await asyncio.to_thread(customers_ws.append_row, new_row, value_input_option='USER_ENTERED')

        # --- Guardado en memoria de sesión para el flujo transaccional ---
        if "Nombre_Completo" in datos_para_sheets:
            state['_customer_name_for_greeting'] = datos_para_sheets["Nombre_Completo"]
        if "Direccion_Principal" in datos_para_sheets:
            state['_last_confirmed_delivery_address_for_order'] = datos_para_sheets["Direccion_Principal"]
            logger.info(f"Dirección guardada en memoria de sesión: {datos_para_sheets['Direccion_Principal']}")
        
        return {"status": "success", "message": "Datos de cliente actualizados exitosamente."}

    except Exception as e:
        logger.error(f"[Tool] Error crítico al escribir en Sheets: {repr(e)}")
        return {"status": "error_internal"}

# En pizzeria_tools.py

async def manage_order_item(tool_context: Any, action: str, item_name: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Añade, elimina o actualiza la cantidad de un ítem en el carrito de la sesión.
    'action' puede ser 'add' o 'remove'.
    """
    state = get_state_from_context(tool_context)
    current_items = state.get('_current_order_items', []).copy()
    action = action.lower()
    item_name_lower = item_name.lower()
    
    if action == "add":
        # Podríamos añadir lógica para agrupar ítems, pero por ahora lo mantenemos simple.
        current_items.append({"name": item_name, "quantity": quantity})
        logger.info(f"[Tool] Añadido al carrito: {quantity}x {item_name}.")
    
    elif action == "remove":
        item_found = False
        # Buscamos el ítem a eliminar (insensible a mayúsculas/minúsculas)
        for i in range(len(current_items) - 1, -1, -1):
            if current_items[i].get("name", "").lower() == item_name_lower:
                removed = current_items.pop(i)
                logger.info(f"[Tool] Eliminado del carrito: {removed['quantity']}x {removed['name']}.")
                item_found = True
                break # Eliminamos solo la primera coincidencia
        
        if not item_found:
            logger.warning(f"[Tool] Se intentó eliminar '{item_name}', pero no se encontró en el carrito.")
            return {"status": "error", "message": f"No encontré '{item_name}' en tu pedido actual para poder eliminarlo."}

    else:
        return {"status": "error", "message": f"La acción '{action}' no es válida. Solo se permite 'add' o 'remove'."}
        
    state['_current_order_items'] = current_items
    logger.info(f"Carrito actual en sesión: {state['_current_order_items']}")
    return {"status": "success", "message": f"Acción '{action}' completada para '{item_name}'."}

async def check_if_order_is_modifiable(tool_context: Any) -> Dict[str, Any]:
    """
    Verifica si el cliente actual tiene un pedido finalizado en los últimos 5 minutos
    de forma robusta, manejando datos potencialmente faltantes.
    """
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    logger.info(f"[Tool] Verificando pedidos recientes para user_id: '{user_id}'")
    if not user_id:
        return {"status": "error", "message": "ID de usuario no encontrado."}

    try:
        loop = asyncio.get_event_loop()
        pedidos_ws = await loop.run_in_executor(None, get_worksheet, 'Pedidos_Registrados')
        if not pedidos_ws:
            return {"status": "error_internal", "message": "No se pudo acceder a la BD de pedidos."}

        all_orders = await loop.run_in_executor(None, pedidos_ws.get_all_records)

        user_orders = [order for order in all_orders if str(order.get('ID_Cliente')) == str(user_id)]

        # <<< INICIO DE LA MEJORA DE ROBUSTEZ >>>
        # Filtramos solo los pedidos que SÍ tienen un Timestamp válido
        valid_user_orders = []
        for order in user_orders:
            if order.get('Timestamp'): # Nos aseguramos que la clave exista y no sea None o vacía
                valid_user_orders.append(order)

        if not valid_user_orders:
            logger.info(f"No se encontraron pedidos previos con timestamp válido para el cliente {user_id}.")
            return {"status": "no_prior_orders"}
        # <<< FIN DE LA MEJORA DE ROBUSTEZ >>>

        valid_user_orders.sort(key=lambda x: datetime.strptime(x['Timestamp'], "%Y-%m-%d %H:%M:%S"), reverse=True)

        latest_order = valid_user_orders[0]
        timestamp_str = latest_order.get('Timestamp')
        order_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        seconds_since_order = (datetime.now() - order_timestamp).total_seconds()

        if seconds_since_order < 300:
            logger.info(f"Pedido reciente encontrado ({int(seconds_since_order)}s). Es modificable.")
            return {
                "status": "modifiable", 
                "order_id": latest_order.get('ID_Pedido'),
                "minutes_ago": int(seconds_since_order / 60)
            }
        elif seconds_since_order < 3600:
             logger.info(f"Pedido en reparto encontrado ({int(seconds_since_order / 60)} min). No es modificable.")
             return {
                "status": "in_delivery", 
                "order_id": latest_order.get('ID_Pedido'),
                "minutes_ago": int(seconds_since_order / 60)
            }
        else:
            logger.info(f"El último pedido es demasiado antiguo ({int(seconds_since_order / 60)} min). No es relevante.")
            return {"status": "not_recent"}

    except Exception as e:
        logger.error(f"[Tool] Error crítico en check_if_order_is_modifiable: {repr(e)}")
        return {"status": "error_internal", "message": f"Error interno: {e}"}

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

async def update_session_flow_state(tool_context: Any, processing_order_sub_phase: str) -> Dict[str, Any]:
    """Cambia la fase de la conversación."""
    state = get_state_from_context(tool_context)
    state['processing_order_sub_phase'] = processing_order_sub_phase
    logger.info(f"[Tool] CAMBIO DE FASE -> {processing_order_sub_phase}")
    return {"status": "success"}

# En pizzeria_tools.py

# En pizzeria_tools.py

# Reemplazar esta función completa en pizzeria_tools.py

async def registrar_pedido_finalizado(tool_context: Any) -> Dict[str, Any]:
    """
    Herramienta final y autosuficiente. Lee todos los datos de la sesión 
    y registra el pedido final en Google Sheets.
    """
    state = get_state_from_context(tool_context)
    logger.info("[Tool] Iniciando registro final de pedido...")

    # 1. Recuperar datos del pedido desde la sesión (state)
    order_items = state.get('_current_order_items', [])
    if not order_items:
        logger.error("[Tool] Intento de registrar un pedido vacío.")
        return {"status": "error", "message": "Error: No se puede registrar un pedido vacío."}

    total_response = await calculate_order_total(tool_context)
    total = total_response.get("subtotal", 0.0)

    # 2. Recuperar datos del cliente desde la sesión (state)
    customer_name = state.get('_customer_name_for_greeting', 'Cliente')
    user_id = state.get('_session_user_id', 'N/A')

    # <<< ¡ESTA ES LA LÍNEA CLAVE DE LA SOLUCIÓN! >>>
    # Leemos la dirección confirmada DIRECTAMENTE de la memoria de la sesión.
    address = state.get('_last_confirmed_delivery_address_for_order', 'No especificada')
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    if address == 'No especificada':
         logger.warning("[Tool] La dirección no fue encontrada en el state al momento de registrar el pedido.")

    # 3. Preparar datos para el registro
    order_id = f"PZ-{str(int(time.time()))[-6:]}"
    items_str = ", ".join([f'{item["quantity"]}x {item.get("name")}' for item in order_items])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. Escribir en la base de datos (Google Sheets) de forma asíncrona
    try:
        loop = asyncio.get_event_loop()
        pedidos_ws = await loop.run_in_executor(None, get_worksheet, 'Pedidos_Registrados')
        if not pedidos_ws:
             return {"status": "error_internal", "message": "No se pudo acceder a la BD de pedidos."}

        nueva_fila = [order_id, user_id, customer_name, address, timestamp, items_str, total, "Pendiente Aprobación"]
        await loop.run_in_executor(None, pedidos_ws.append_row, nueva_fila, value_input_option='USER_ENTERED')

        # 5. Guardar la marca de tiempo para la ventana de modificación
        state['_order_finalized_timestamp'] = time.time()

        logger.info(f"--- Pedido {order_id} REGISTRADO EN GOOGLE SHEETS ---")
        logger.info(f"  -> Cliente: {customer_name}, Dirección: {address}")

        # 6. Limpiar el estado del pedido actual para la siguiente interacción
        state['_current_order_items'] = []
        state['_order_subtotal'] = 0.0
        state['_last_confirmed_delivery_address_for_order'] = None

        return {"status": "success", "message": f"¡Gracias, {customer_name}! Tu pedido #{order_id} por S/ {total:.2f} ha sido registrado y se enviará a: {address}."}

    except Exception as e:
        logger.error(f"[Tool] Error crítico al registrar pedido en Sheets: {repr(e)}")
        return {"status": "error_internal", "message": "Tuvimos un problema al registrar tu pedido final."}

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

async def get_saved_addresses(tool_context: Any) -> Dict[str, Any]:
    """
    Recupera las direcciones guardadas (Principal y Secundaria) para el cliente actual.
    Reutiliza la lógica de get_customer_data para no duplicar código.
    """
    state = get_state_from_context(tool_context)
    user_id = state.get('_session_user_id')
    logger.info(f"[Herramienta: get_saved_addresses] Buscando direcciones para user_id: '{user_id}'")
    if not user_id:
        return {"status": "error_no_client_id", "message": "ID de usuario no encontrado en sesión."}
    
    # Reutilizamos la herramienta que ya busca al cliente
    customer_data_response = await get_customer_data(tool_context)
    
    if customer_data_response.get("status") == "found":
        customer_data = customer_data_response.get("data", {})
        dir_principal = customer_data.get('Direccion_Principal', '').strip()
        dir_secundaria = customer_data.get('Direccion_Secundaria', '').strip()
        
        addresses = {}
        if dir_principal: addresses['Direccion_Principal'] = dir_principal
        if dir_secundaria: addresses['Direccion_Secundaria'] = dir_secundaria
            
        if addresses:
            logger.info(f"Direcciones encontradas: {addresses}")
            return {"status": "success", "addresses": addresses}
    
    # Si el cliente no fue encontrado, o fue encontrado pero no tiene direcciones
    logger.info(f"No se encontraron direcciones guardadas para el cliente {user_id}.")
    return {"status": "no_addresses_found", "message": "No tienes direcciones guardadas."}

