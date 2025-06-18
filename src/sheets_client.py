# Contenido COMPLETO y CORREGIDO para sheets_client.py

import gspread
from google.oauth2.service_account import Credentials 

# Define el alcance (scope) de los permisos.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file' 
]

# Ruta al archivo JSON de credenciales de la cuenta de servicio
CREDS_FILE = 'google-credentials.json' 

# Nombre de tu Hoja de Cálculo en Google Drive (lo dejamos por si volvemos a usarlo, pero open_by_url no lo usa)
SPREADSHEET_NAME = 'PizzeriaBotDB' 

_spreadsheet = None 

def _get_spreadsheet_client():
    """
    Función interna para autenticarse con Google Sheets usando credenciales de cuenta de servicio
    y abrir la hoja de cálculo especificada por URL. Cachea el objeto spreadsheet.
    """
    global _spreadsheet
    if _spreadsheet is None: 
        try:
            creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
            client = gspread.authorize(creds)
            
            # --- LÍNEA MODIFICADA PARA USAR LA URL CORRECTAMENTE ---
            # !!! ASEGÚRATE DE PEGAR AQUÍ LA URL COMPLETA Y CORRECTA DE TU HOJA DE CÁLCULO !!!
            spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nB8F00oaSAUoh4QJB3lcIpJryLEgk-Wi_BZJbZhLmik/edit?gid=304647370#gid=304647370" # <-- REEMPLAZA ESTA URL DE EJEMPLO CON LA TUYA
            # Nota: A menudo es mejor quitar la parte final de la URL como "?gid=..." o "#gid=..."
            # Prueba con la URL completa primero, si falla, prueba solo hasta "/edit"
            # Ejemplo sin #gid: "https://docs.google.com/spreadsheets/d/1nB8F00oaSAUoh4QJB3lcIpJryLEgk-Wi_BZJbZhLmik/edit"

            _spreadsheet = client.open_by_url(spreadsheet_url)
            # Si abres por URL, el SPREADSHEET_NAME que tengas arriba no se usa para esta operación,
            # pero es bueno saber el nombre real para los logs.
            actual_spreadsheet_name = _spreadsheet.title
            print(f"[sheets_client] Conexión exitosa a la Hoja de Cálculo por URL. Nombre: '{actual_spreadsheet_name}'")
        except Exception as e:
            print(f"[sheets_client] Error CRÍTICO al conectar o abrir la Hoja de Cálculo por URL.")
            print(f"[sheets_client] Tipo de error: {type(e)}")
            print(f"[sheets_client] Detalles del error: {repr(e)}")
            _spreadsheet = "ERROR" 
            return None
    
    if _spreadsheet == "ERROR": 
        return None
    return _spreadsheet

def get_worksheet(worksheet_name: str):
    """
    Obtiene una pestaña (worksheet) específica de la hoja de cálculo principal.
    """
    spreadsheet = _get_spreadsheet_client() 
    
    if spreadsheet: 
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"[sheets_client] Acceso exitoso a la pestaña: '{worksheet_name}'")
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            # Usamos spreadsheet.title para obtener el nombre real de la hoja abierta por URL
            print(f"[sheets_client] Error: Pestaña '{worksheet_name}' no encontrada en la Hoja de Cálculo '{spreadsheet.title}'. Verifica el nombre exacto.")
        except Exception as e:
            print(f"[sheets_client] Error al intentar obtener la pestaña '{worksheet_name}':")
            print(f"[sheets_client] Tipo de error: {type(e)}")
            print(f"[sheets_client] Detalles del error: {repr(e)}")
    else:
        print(f"[sheets_client] No se pudo obtener la pestaña '{worksheet_name}' porque no se pudo conectar a la Hoja de Cálculo.")
        
    return None

if __name__ == '__main__':
    print("-----------------------------------------------------")
    print("Probando el módulo sheets_client.py (abriendo por URL)...")
    print("-----------------------------------------------------")
    
    print("\n[Prueba 1] Intentando acceder a la pestaña 'Clientes':")
    clientes_ws = get_worksheet('Clientes')
    if clientes_ws:
        print("Resultado Prueba 1: Acceso a 'Clientes' exitoso.")
        try:
            headers = clientes_ws.row_values(1) 
            print(f"Encabezados de 'Clientes': {headers}")
        except Exception as e:
            print(f"Error al leer encabezados de 'Clientes': {repr(e)}")
    else:
        print("Resultado Prueba 1: Fallo al obtener la pestaña 'Clientes'. Revisa los mensajes de error anteriores y tu configuración.")

    print("-----------------------------------------------------")
    print("\n[Prueba 2] Intentando acceder a una pestaña inexistente ('PestañaQueNoExiste'):")
    inexistente_ws = get_worksheet('PestañaQueNoExiste')
    if inexistente_ws is None:
        print("Resultado Prueba 2: Correcto, la pestaña inexistente devolvió None (o hubo un error de conexión previo).")
    else:
        print("Resultado Prueba 2: INESPERADO, se obtuvo un objeto para una pestaña que no debería existir.")
    print("-----------------------------------------------------")
    print("Pruebas de sheets_client.py finalizadas.")