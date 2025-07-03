# src/pizzeria_callbacks.py

import logging
from typing import Any, Dict, Optional
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool

# Usamos el mismo logger que en los otros archivos para consistencia
logger = logging.getLogger(__name__)

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from typing import Optional

def log_before_model_call(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Callback que loggea el prompt que se envía al LLM."""
    agent_name = callback_context.agent_name
    logger.info(f"[[🧠 MODEL_CALL - PROMPT]] Para Agente '{agent_name}':")
    # El prompt completo suele estar en la última parte del contenido
    if llm_request.contents:
        for part in llm_request.contents[-1].parts:
             logger.info(f"  -> {part.text}")
    return None # Devuelve None para permitir que la llamada continúe

def log_after_model_call(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """Callback que loggea la respuesta cruda del LLM."""
    agent_name = callback_context.agent_name
    logger.info(f"[[🧠 MODEL_CALL - RESPONSE]] De Agente '{agent_name}':")
    # La decisión del LLM (llamar a una función) está en las partes de la respuesta
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.function_call:
                fc = part.function_call
                logger.info(f"  <- [Function Call] Herramienta: {fc.name}, Args: {dict(fc.args)}")
    return None # Devuelve None para no interferir con la respuesta


def log_before_tool_call(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Este callback se ejecuta ANTES de cada llamada a una herramienta.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    
    logger.info(
        f"[[CALLBACK - ANTES]] Agente '{agent_name}' está a punto de llamar a la Herramienta ---> '{tool_name}'"
    )
    logger.info(f"    -> Argumentos: {args}")
    
    return None

def log_after_tool_call(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict[str, Any]
) -> Optional[Dict]:
    """
    Este callback se ejecuta DESPUÉS de cada llamada a una herramienta.
    """
    agent_name = tool_context.agent_name
    tool_name = tool.name
    
    response_str = str(tool_response)
    if len(response_str) > 300:
        response_str = response_str[:300] + "..."
        
    logger.info(
        f"[[CALLBACK - DESPUÉS]] Herramienta '{tool_name}' ejecutada por Agente '{agent_name}'"
    )
    logger.info(f"    <- Resultado: {response_str}")
    
    return None