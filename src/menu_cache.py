import json
import logging

logger = logging.getLogger(__name__)

# Esta variable global guardará nuestro menú en memoria.
_MENU_DATA = None # Lo iniciamos como None para ser más explícitos

def load_menu_from_json(file_path: str = 'menu.json'):
    """
    Carga los datos del menú desde un archivo JSON a la variable global _MENU_DATA.
    Esta función se debe llamar UNA SOLA VEZ cuando el bot se inicia.
    """
    global _MENU_DATA
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            _MENU_DATA = json.load(f)
        logger.info(f"✅ Menú cargado exitosamente en caché desde '{file_path}'. Se encontraron {len(_MENU_DATA)} ítems.")
    except FileNotFoundError:
        logger.error(f"❌ ERROR CRÍTICO: No se encontró el archivo del menú en '{file_path}'.")
        _MENU_DATA = {} # Usamos un diccionario vacío en caso de error
    except json.JSONDecodeError:
        logger.error(f"❌ ERROR CRÍTICO: El archivo del menú '{file_path}' contiene un JSON inválido.")
        _MENU_DATA = {}

def get_menu() -> list:
    """
    Devuelve SIEMPRE una lista de los ítems del menú.
    Si la caché es un diccionario (formato antiguo), lo convierte a una lista de sus valores.
    """
    if _MENU_DATA is None:
        load_menu_from_json()
    
    # <<< LA SOLUCIÓN DEFINITIVA ESTÁ AQUÍ >>>
    if isinstance(_MENU_DATA, dict):
        # Si la caché es un diccionario, devuelve una lista de sus valores (los objetos de las pizzas)
        return list(_MENU_DATA.values())
    
    # Si ya es una lista (formato correcto), la devuelve tal cual
    return _MENU_DATA