Estado del Proyecto: PizzeríaBot (24 de Mayo, 2025)

1\. Descripción General del Proyecto

**PizzeríaBot** es un sistema de chatbot inteligente diseñado para
automatizar y mejorar la experiencia de toma de pedidos para una
pizzería. El proyecto se está desarrollando en Python utilizando el
**Agent Development Kit (ADK) de Google**, con el objetivo de integrarse
eventualmente con plataformas de mensajería como WhatsApp. La gestión de
datos (menú, clientes, pedidos) se realiza a través de **Google
Sheets**. El tono de comunicación del bot se define como amigable,
proactivo, directo y formal.

El sistema se basa en una arquitectura multi-agente, donde cada agente
se especializa en una parte del flujo conversacional:

Gestión de clientes (registro, identificación).

Toma de pedidos (navegación de menú, adición/modificación de ítems).

Confirmación de detalles de entrega.

(Futuro) Confirmación de pago y procesamiento final del pedido.

Un agente raíz (RootAgent) orquesta el flujo entre los agentes
especializados.

2\. Logros y Avances Hasta la Fecha

Hemos alcanzado hitos significativos en el desarrollo de los componentes
centrales del sistema:

2.1. Agentes Implementados y Funcionales:

**CustomerManagementAgent_v1**:

**Estado:** ✅ Altamente Funcional.

**Capacidades:**

Saluda a los usuarios nuevos y existentes.

Verifica la existencia de clientes usando la herramienta
get_customer_data.

Registra nuevos clientes (obteniendo Nombre_Completo) y actualiza datos
de clientes existentes mediante register_update_customer.

Personaliza el saludo para clientes recurrentes.

Maneja el \_session_user_id de forma robusta a través de un callback.

**OrderTakingAgent_v1**:

**Estado:** 🟢 Muy Avanzado, con un punto crítico identificado
recientemente.

**Capacidades Verificadas:**

Inicia la conversación ofreciendo el menú o la toma directa del pedido.

Utiliza manage_order_item para añadir ítems.

Maneja la ambigüedad de ítems (ej. diferentes tamaños de pizza)
presentando opciones al usuario (obtenidas de get_menu_item_details).

Responde a consultas sobre detalles de platos (get_menu_item_details) y
promociones (get_active_promotions).

Permite modificar la cantidad de un ítem (manage_order_item con
action=\'update_quantity\').

Permite quitar un ítem del pedido (manage_order_item con
action=\'remove\').

Muestra el resumen del pedido actual (view_current_order).

Finaliza su parte de la selección de ítems mostrando un resumen y un
mensaje de transición claro para el siguiente agente.

**DeliveryConfirmationAgent_v1**:

**Estado:** 🟢 Funcionalidad Base Implementada, con ajustes recientes en
su lógica de manejo de direcciones.

**Capacidades Verificadas:**

Inicia su flujo llamando a view_current_order para obtener el pedido del
agente anterior.

Presenta el resumen del pedido al cliente y solicita confirmación
explícita del contenido.

Si el cliente no confirma el contenido, está instruido para devolver el
control.

Si el contenido es confirmado, procede a gestionar la dirección de
envío:

Llama a get_saved_addresses para buscar direcciones existentes.

Si no hay direcciones, solicita una nueva al cliente.

Confirma verbalmente la dirección proporcionada.

Intenta guardar/actualizar la dirección usando register_update_customer.
(Manejo de error mejorado).

Llama a calculate_delivery_cost con la dirección confirmada.

Informa el costo y tiempo estimado de envío.

Finaliza su interacción con un mensaje de transición indicando que se
realizará una \"última verificación\" antes de pasar a cocina.

**RootAgent_v1 (Orquestador Principal):**

**Estado:** 🟢 Lógica de Orquestación Básica y Verificación de Datos
Implementada.

**Capacidades Verificadas:**

Transfiere correctamente el control al CustomerManagementAgent_v1 al
inicio de una nueva conversación.

Transfiere correctamente el control al OrderTakingAgent_v1 después de
que CustomerManagementAgent_v1 completa el registro/identificación.

Transfiere correctamente el control al DeliveryConfirmationAgent_v1
después de que OrderTakingAgent_v1 finaliza la selección de ítems.

Llama a la herramienta get_customer_data (versión mejorada) después de
que DeliveryConfirmationAgent_v1 completa su parte.

Reacciona correctamente a los diferentes status devueltos por
get_customer_data:

\'complete\': Procede con un mensaje indicando que el pedido se
procesará para cocina.

\'not_found\': Transfiere al CustomerManagementAgent_v1 para un registro
completo.

\'incomplete\' (específicamente si falta Direccion_Principal pero el
nombre está): Transfiere al DeliveryConfirmationAgent_v1 para que este
solicite la dirección.

2.2. Herramientas (pizzeria_tools.py):

**get_customer_data**: ✅ Mejorada para devolver status, data y
missing_fields, funcionando correctamente en los escenarios probados.

**register_update_customer**: ✅ Funcional para registrar nuevos
clientes y actualizar existentes. Maneja correctamente el caso de
cliente nuevo vs. existente.

**get_menu_item_details**: ✅ Funcional para buscar ítems y devolver
detalles o opciones de clarificación (incluyendo id_plato, nombre_plato,
precio para las opciones).

**manage_order_item**: ✅ Funcional para las acciones add,
update_quantity, y remove.

**view_current_order**: ✅ Funcional para mostrar el pedido actual o
indicar si está vacío.

**get_active_promotions**: ✅ Funcional.

**get_saved_addresses**: ✅ Mejorada y depurada. Ahora devuelve status:
\"no_addresses_found\" correctamente para clientes nuevos sin
direcciones guardadas. Los prints de depuración fueron clave para esto.

**calculate_delivery_cost**: ✅ Funcional con la lógica de ejemplo para
costos y tiempos basados en zonas.

2.3. Infraestructura y Lógica General:

**Manejo de \_session_user_id**: Implementado de forma robusta mediante
el callback focused_set_user_id_callback, asegurando que las
herramientas y agentes tengan el contexto correcto del usuario.

**Estructura Multi-Agente con Transferencia:** El concepto de transferir
el control entre agentes (manejado por el RootAgent o por los propios
agentes al finalizar su tarea) está tomando forma.

3\. Estado Actual y Dificultades (Basado en el Último Log)

A pesar de los grandes avances, el último flujo de prueba completo
(run_complete_pizzeria_flow_via_root_agent()) reveló algunos puntos
críticos:

3.1. Problema Principal Actual: OrderTakingAgent_v1 - Adición de Ítems
Post-Clarificación

**Dificultad:** Cuando el OrderTakingAgent_v1 presenta opciones de
clarificación al usuario (ej., diferentes tamaños de pizza incluyendo el
precio en el string que muestra, como \"Pizza Americana - Grande
(S/38.90)\"), y el usuario selecciona una de estas opciones, el agente
intenta añadir el ítem usando ese string completo (con el precio) en la
llamada a manage_order_item. La herramienta get_menu_item_details (usada
internamente por manage_order_item) no encuentra una coincidencia exacta
para \"Pizza Americana - Grande (S/38.90)\" en la hoja \"Menú\", ya que
el nombre del ítem allí es probablemente solo \"Pizza Americana -
Grande\".

**Impacto:** Esto causa que el ítem no se añada al pedido. Si es el
único ítem, el pedido queda vacío, y el OrderTakingAgent_v1 no puede
pasar un pedido válido al DeliveryConfirmationAgent_v1, bloqueando el
flujo completo.

**Cómo se está afrontando:** La solución propuesta y pendiente de
implementación/verificación final es ajustar la instruction del
OrderTakingAgent_v1 (específicamente el Paso 2.e) para que, después de
la clarificación, utilice el nombre_plato base (obtenido de las options
devueltas por la herramienta) para la llamada a manage_order_item, en
lugar del string completo que el LLM formuló para el usuario.

3.2. Manejo de Múltiples Ítems y Negativos en un Solo Input por
OrderTakingAgent_v1

**Dificultad:** Cuando el usuario dice \"Una pizza americana grande y
dos gaseosas personales por favor\", el OrderTakingAgent_v1 (en el
último log) se enfocó en la \"Pizza Americana\" y pidió clarificación,
pero no abordó inmediatamente el hecho de que \"gaseosas personales\" no
existen. Sería ideal un manejo más integral.

**Cómo se está afrontando:** Esto es más un refinamiento de la
instruction del OrderTakingAgent_v1. Se podría instruir para que, ante
un input múltiple, intente validar todos los ítems mencionados y reporte
todos los problemas (no encontrados, ambiguos) de una vez o
secuencialmente antes de proceder con los válidos. Por ahora, el foco
está en el problema de adición post-clarificación.

3.3. \"Alucinaciones\" o Desviaciones del LLM de las Instrucciones

**Dificultad:** Hemos observado casos donde los LLM de los agentes (ej.
DeliveryConfirmationAgent_v1 con la dirección fantasma, o el RootAgent
omitiendo mensajes de transición antes de una transferencia) no siguen
al pie de la letra instrucciones muy explícitas, especialmente si
perciben un camino más directo al objetivo o si los ejemplos en la
instruction son muy influyentes.

**Cómo se está afrontando:**

Reforzando las instructions con lenguaje más imperativo (\"ACCIÓN
OBLIGATORIA\", \"DEBES informar EXACTAMENTE así\", \"NO INVENTES\...\").

Reordenando la lógica en las instructions para priorizar chequeos
críticos (ej. el caso no_addresses_found para get_saved_addresses).

Aceptando pequeñas desviaciones si el flujo lógico principal no se rompe
y el objetivo se cumple.

Asegurando que las herramientas devuelvan datos claros y estructurados
para minimizar la ambigüedad para el LLM.

3.4. Flujo de Prueba y Sincronización de Inputs del Usuario

**Dificultad:** En las pruebas de flujo completo, los inputs del
\"usuario simulado\" en el script no siempre estaban perfectamente
alineados con la respuesta anterior del bot, causando que algunos inputs
llegaran al agente \"equivocado\" o en un contexto inesperado.

**Cómo se está afrontando:** La necesidad de reestructurar las funciones
de prueba (como run_complete_pizzeria_flow_via_root_agent()) para que
cada input del usuario sea una respuesta lógica y secuencial al output
previo del bot. Esto implica capturar la respuesta del agente y usarla
para informar el siguiente input simulado.

4\. Lo que Falta y Próximos Pasos

**Resolver el Problema Crítico en OrderTakingAgent_v1 (Prioridad #1):**

Implementar y probar el ajuste en la instruction (Paso 2.e) para que use
el nombre_plato base después de la clarificación.

**Reestructurar y Completar la Prueba
run_complete_pizzeria_flow_via_root_agent():**

Asegurar un diálogo secuencial y realista.

Probar el flujo donde el RootAgent detecta status: \"incomplete\" (ej.
cliente con nombre pero sin dirección después de
DeliveryConfirmationAgent_v1) y ver si transfiere correctamente al
agente adecuado para recolectar la información faltante, y si luego
re-verifica.

**Desarrollo del RootAgent_v1 (Continuación):**

Refinar su instruction para manejar todas las transiciones entre
sub-agentes de manera fluida.

Implementar la lógica para cuando un sub-agente le devuelve el control
(ej. después de que CustomerManagementAgent_v1 registra un nombre, el
RootAgent debe saber pasar a OrderTakingAgent_v1).

**Implementar el Flujo de \"Aprobación de Cocina\":**

Diseñar el agente o herramienta (OrderProcessingAgent?) que:

Tome el pedido confirmado y los datos del cliente del state (después de
la verificación del RootAgent).

Envíe el pedido a Telegram para aprobación del personal.

Actualice el estado del pedido en Google Sheets a \"ESPERANDO APROBACIÓN
COCINA\".

Crear el mecanismo para recibir la respuesta de aprobación/rechazo desde
Telegram.

Diseñar el agente o herramienta que:

Procese la respuesta del trabajador.

Actualice el estado del pedido en Sheets (\"APROBADO, EN PREPARACIÓN\" o
\"RECHAZADO\").

Notifique proactivamente al cliente el nuevo estado y, si fue aprobado,
pregunte \"¿Te puedo ayudar en algo más?\".

**Desarrollar Agentes Pendientes (Según documento de avance):**

PaymentConfirmationAgent (si se decide separar del flujo de
entrega/aprobación).

DailyReportAgent.

**Integración con Plataforma de Mensajería (WhatsApp/Telegram):** Fase
final de implementación.

**Mejoras Adicionales:**

Cacheo de Menú/Promociones.

Manejo de errores más robusto en todas las herramientas y agentes.

Refinamiento continuo de las instructions de los LLM Agents basado en
pruebas.

5\. Conclusión General

El proyecto PizzeríaBot ha avanzado considerablemente. Los agentes
individuales para gestión de clientes, toma de pedidos y confirmación de
entrega están en etapas avanzadas de funcionalidad. La herramienta
get_customer_data ha sido mejorada exitosamente. El RootAgent está
comenzando a orquestar el flujo y a tomar decisiones basadas en datos.

La principal dificultad actual radica en asegurar que el
OrderTakingAgent_v1 maneje correctamente la adición de ítems después de
una clarificación de opciones presentadas con precio. Una vez resuelto
esto, y con una reestructuración de la función de prueba principal,
podremos validar el flujo orquestado por el RootAgent de manera más
efectiva y proceder con la implementación del ciclo de aprobación de
cocina.

El enfoque iterativo de desarrollo, prueba y refinamiento está
demostrando ser efectivo para identificar y abordar los desafíos
inherentes al trabajo con LLMs y sistemas multi-agente.\
\
Estado del Proyecto: PizzeríaBot (26 de Mayo, 2025)

**1. Descripción General del Proyecto** *(Sin cambios respecto a tu
versión, sigue siendo la misma base: PizzeríaBot, Python, ADK de Google,
Google Sheets, tono amigable, etc. Arquitectura multi-agente.)*

**2. Logros y Avances Hasta la Fecha (Actualizado)**

Hemos alcanzado hitos significativos en el desarrollo y depuración de
los componentes centrales del sistema, logrando un flujo conversacional
coherente para el \"camino feliz\" de un nuevo cliente.

**2.1. Agentes Implementados y Funcionales (Detalle Actualizado):**

**CustomerManagementAgent_v1 (Versión v2.4 - Máxima Restricción)**

**Estado:** ✅ **Altamente Funcional y Estable.**

**Capacidades:**

Saluda a los usuarios.

Verifica la existencia de clientes usando get_customer_data.

**Comportamiento Corregido:** Pide el nombre completo a nuevos clientes
y **espera la respuesta del usuario** antes de intentar cualquier acción
de registro.

**Comportamiento Corregido:** Registra nuevos clientes (obteniendo
Nombre_Completo) de forma correcta y en un solo intento (después de la
respuesta del usuario) usando register_update_customer.

Identifica clientes existentes y los saluda adecuadamente.

Finaliza su turno correctamente, pasando el control para la toma del
pedido.

**Mejoras Realizadas:** Se refinó exhaustivamente su instruction (hasta
la v2.4) para asegurar un orden estricto de operaciones y evitar
llamadas prematuras a herramientas, logrando un comportamiento
predecible y correcto.

**OrderTakingAgent_v1 (Versión v7 - Parámetros Explícitos y Finalización
Precisa)**

**Estado:** ✅ **Altamente Funcional y Estable.**

**Capacidades:**

**Comportamiento Corregido:** Procesa el pedido inicial del usuario
inmediatamente después de la transición desde CustomerManagementAgent_v1
(problema de \"pérdida de mensaje\" resuelto).

Utiliza manage_order_item con todos los parámetros requeridos (action,
nombre_plato_o_id, cantidad, instrucciones_especiales), gracias a
instructions explícitas y un parámetro por defecto en la herramienta.

Utiliza get_menu_item_details (con búsqueda flexible por palabras clave)
para buscar ítems y manejar ambigüedad, presentando opciones con precio
si es necesario.

Confirma ítems añadidos y pregunta si el usuario desea algo más.

Maneja la finalización del pedido por parte del usuario (ej. \"eso es
todo\").

Llama a view_current_order para obtener el resumen.

**Comportamiento Corregido:** Proporciona un mensaje de finalización
exacto y conciso, indicando que se procederá con la confirmación y los
detalles de entrega, y que su tarea termina ahí.

**Mejoras Realizadas:**

Se ajustó pizzeria_tools.py para que manage_order_item tenga
instrucciones_especiales como opcional con valor por defecto, aumentando
la robustez.

Se refinó su instruction (hasta la v7) para forzar la llamada inmediata
a manage_order_item con todos los parámetros y para asegurar una
respuesta conversacional después de la ejecución de la herramienta.

Se precisó su mensaje de finalización para facilitar una transición
limpia al siguiente agente.

**DeliveryConfirmationAgent_v1 (Versión v2 - Finalización Explícita)**

**Estado:** ✅ **Funcional para el \"Camino Feliz\"; Próximo a
Refinamiento.**

**Capacidades:**

Inicia correctamente después de la transición desde OrderTakingAgent_v1.

Llama a view_current_order y presenta el resumen del pedido para
confirmación.

Procesa la confirmación del pedido por parte del usuario.

Llama a get_saved_addresses y, si no hay direcciones, pide una nueva.

Recibe la dirección proporcionada por el usuario y la repite para
confirmación.

**Comportamiento Corregido:** Después de que el usuario confirma la
dirección, el agente ahora **correctamente utiliza las herramientas
register_update_customer (para guardar la dirección) y
calculate_delivery_cost**.

Informa el costo y el tiempo estimado de entrega.

**Comportamiento Corregido:** Da su mensaje final de cierre
(\"¡Excelente! Hemos registrado todos los detalles\...\") indicando que
su tarea ha concluido.

**Mejoras Realizadas:**

Se ajustó su instruction (hasta la v2) para que, después de informar el
costo de envío, proceda obligatoriamente a dar su mensaje final de
\"verificación/todo está en marcha\".

**Pendiente de Refinamiento (Próximo Paso):** Aunque el flujo actual
funciona bien con el script, se podría mejorar su robustez para manejar
casos donde el usuario proporcione la dirección en el mismo mensaje que
confirma el pedido (similar al problema de \"pérdida de mensaje\" que
tenía OrderTakingAgent_v1).

**RootAgent_v1 (Versión v1 - Original)**

**Estado:** ✅ **Funcional para Orquestación Básica.**

**Capacidades:**

Maneja el inicio de la conversación y transfiere correctamente a
CustomerManagementAgent_v1.

Transfiere correctamente de CustomerManagementAgent_v1 a
OrderTakingAgent_v1.

Transfiere correctamente de OrderTakingAgent_v1 a
DeliveryConfirmationAgent_v1.

**Pendiente de Implementación/Prueba (Próximo Paso):** El Paso 4 de su
instruction (VERIFICACIÓN DE DATOS DEL CLIENTE después de
DeliveryConfirmationAgent_v1 y las acciones subsecuentes) aún no ha sido
probado exhaustivamente ni implementado en detalle.

**2.2. Herramientas (pizzeria_tools.py) (Actualizado):**

- get_customer_data: Funcional.

- register_update_customer: Funcional, maneja nuevos registros y
  actualizaciones.

- get_menu_item_details: **Mejorada significativamente** con búsqueda
  flexible por palabras clave.

- manage_order_item: **Mejorada** para ser más robusta (parámetro
  instrucciones_especiales con valor por defecto). Funcional.

- view_current_order: Funcional.

- get_saved_addresses: Funcional.

- calculate_delivery_cost: Funcional.

**2.3. Script de Prueba (run_complete_pizzeria_flow_LOGICO)
(Actualizado):**

- **Estado:** ✅ **Altamente Funcional y Robusto para el \"Camino
  Feliz\".**

- Se ha transformado de un script rígido a uno lógico que reacciona a
  las respuestas del bot.

- Se han añadido múltiples DEBUG PRINTS y se han refinado las
  condiciones if para manejar las variaciones del lenguaje del LLM, lo
  que fue **clave para superar los bloqueos y entender el comportamiento
  real del sistema**.

- El script ahora navega con éxito todo el flujo desde el saludo inicial
  hasta la finalización por parte del DeliveryConfirmationAgent_v1.

**3. Resumen de Desafíos Superados (Actualizado)**

- **Llamadas Prematuras a Herramientas (CustomerManagementAgent_v1):**
  Solucionado con instructions v2.4 extremadamente estrictas sobre el
  orden de los turnos y acciones.

- **Falta de Parámetros en Llamadas a Herramientas
  (OrderTakingAgent_v1):** Solucionado haciendo la herramienta
  (manage_order_item) más robusta (parámetros por defecto) y con
  instructions v7 muy explícitas para el agente.

- **Agente No Genera Respuesta Textual Después de Herramienta
  (OrderTakingAgent_v1):** Solucionado con instructions v7 que fuerzan
  una respuesta conversacional post-herramienta.

- **\"Pérdida de Mensaje\" en Transición a OrderTakingAgent_v1:**
  Solucionado con instruction v7 que le indica al agente procesar el
  último mensaje del usuario como un posible pedido.

- **Fragilidad del Script de Prueba:** Solucionado mediante la adición
  de DEBUG PRINTS detallados y la creación de condiciones if más
  flexibles y robustas para interpretar las respuestas del bot. Esto fue
  un proceso iterativo crucial.

<!-- -->

- **DeliveryConfirmationAgent_v1 No Daba Mensaje Final:** Solucionado
  con instruction v2 que lo obliga a dar su mensaje de cierre.

**4. Próximos Pasos y Enfoque (Actualizado)**

Con el \"camino feliz\" principal funcionando sólidamente, los próximos
pasos son:

**Modo de Prueba Interactivo:**

- **Acción:** Habilitar y realizar pruebas conversando directamente con
  el bot para evaluar la naturalidad y detectar nuevos comportamientos o
  fallos en escenarios no cubiertos por el script.

- **Objetivo:** Recopilar logs de estas sesiones interactivas para un
  análisis conjunto.

  **Probar e Implementar el Paso 4 del RootAgent_v1:**

- **Acción:** Extender el script de prueba lógico (o usar el modo
  interactivo) para verificar si el RootAgent, después de que
  DeliveryConfirmationAgent_v1 finaliza, llama a get_customer_data y
  toma las decisiones correctas según si los datos del cliente están
  completos.

- **Objetivo:** Asegurar que el ciclo de verificación de datos del
  RootAgent funcione y que pueda re-transferir a agentes específicos si
  falta información.

  **Refinamiento Proactivo del DeliveryConfirmationAgent_v1:**

- **Acción (Opcional por ahora, pero recomendado):** Considerar
  actualizar la instruction del DeliveryConfirmationAgent_v1 para que,
  al igual que el OrderTakingAgent_v1, revise el mensaje del usuario en
  su primer turno en busca de una dirección (si el usuario la
  proporciona junto con la confirmación del pedido), para evitar la
  \"pérdida de mensaje\".

  **Manejo de Casos de Uso Adicionales y Errores (Expansión):**

- Cliente existente.

- Usuario quiere modificar el pedido durante la confirmación de entrega.

<!-- -->

- OrderTakingAgent_v1 informando sobre ítems no encontrados en un pedido
  inicial múltiple (ej. \"pizza y gaseosa personal\").

<!-- -->

- Manejo de errores de herramientas de forma más elegante por parte de
  los agentes.

  **Desarrollar Agentes Pendientes:**

<!-- -->

- PaymentConfirmationAgent.

- DailyReportAgent.

- KitchenApprovalAgent (requiere definir claramente su interacción y
  herramientas).

  **Integración con Plataforma de Mensajería.**

  **Mejoras Adicionales (Continuo):**

<!-- -->

- Cacheo de Menú/Promociones.

- Refinamiento continuo de todas las instructions basado en más pruebas.

**5. Conclusión General (Actualizada)**

El proyecto PizzeríaBot ha demostrado una **progresión excepcional**.
Hemos superado los desafíos técnicos y de lógica de los LLM para
establecer un flujo conversacional funcional y coherente a través de los
tres agentes principales. La estrategia de depuración detallada del
script de prueba y el refinamiento iterativo de las instructions de los
agentes ha sido fundamental para este éxito.

El sistema está ahora en un punto donde el \"camino feliz\" está
validado, y podemos proceder con confianza a probarlo interactivamente y
luego expandir su funcionalidad y robustez para cubrir más escenarios y
los agentes restantes. El CustomerManagementAgent_v1 y el
OrderTakingAgent_v1 están en un estado muy maduro, y el
DeliveryConfirmationAgent_v1 ha demostrado su capacidad de seguir su
flujo y usar herramientas correctamente.

¡Perfecto, amigo! Entiendo tu entusiasmo por esta etapa de planificación
y diseño. Es el momento ideal para plasmar la visión y la estrategia.
Actualizar el \"Plan de Desarrollo\" es una excelente idea para mantener
todo organizado.

Basado en nuestras últimas conversaciones, aquí tienes un borrador de
cómo podríamos estructurar esa actualización, incorporando el \"Enfoque
2.1\" y las nuevas ideas.

**Actualización del Plan de Desarrollo: PizzeríaBot (28 de Mayo, 2025)**

**1. Visión General y Enfoque Actual (Enfoque 2.1)**

- **Reafirmación del Objetivo**: PizzeríaBot sigue siendo un chatbot
  inteligente para automatizar pedidos, integrado con Telegram y usando
  Google Sheets como backend. El tono es \"Angelo de Pizzería San
  Marzano\", amigable, formal y eficiente.

- **Evolución de la Arquitectura de Agentes (Enfoque 2.1 - Orquestador
  Central Inteligente)**:

  - **RootAgent_v1 (Orquestador Principal)**:

    - **Rol Centralizado**: Actúa como el principal oyente e intérprete
      de las intenciones del usuario en casi todos los turnos.

    - **Gestión de Estado Explícita**: Utiliza variables en
      session.state (como current_main_goal y
      processing_order_sub_phase) para rastrear el objetivo general y la
      sub-fase actual de la conversación. (Se requiere implementar la
      herramienta update_session_flow_state y que RootAgent_v1 la use).

    - **Orquestación de Fases**: Delega fases completas de la
      interacción a agentes especializados.

    - **Manejo de Intenciones Diversas Post-CMA**: Después de que
      CustomerManagementAgent_v1 identifica/saluda al cliente,
      RootAgent_v1 analiza la respuesta del usuario para determinar si
      es un pedido, una queja, una pregunta general, etc., y actúa en
      consecuencia.

    - **Manejo de \"Escape Hatch\"**: Recibe el control de sub-agentes
      si el usuario introduce una intención fuera del alcance del
      sub-agente actual, re-evalúa y re-dirige.

    - **Responsabilidades Directas**: Finalización del pedido (llamando
      a get_customer_data, view_current_order,
      registrar_pedido_finalizado), manejo de preguntas generales
      básicas, y potencialmente cancelaciones de pedidos.

  - **CustomerManagementAgent_v1 (CMA - Experto en Clientes y Saludo
    Único)**:

    - **Responsabilidad Única**: Siempre es el primer agente
      especializado en interactuar con el usuario (después de la
      derivación inicial de Root).

    - **Flujo**: Llama a get_customer_data. Saluda como \"Angelo de
      Pizzería San Marzano\" (diferenciando entre usuario
      nuevo/conocido). Si es nuevo, solicita nombre y llama a
      register_update_customer. Finaliza su interacción preguntando
      \"¿En qué te puedo servir esta vez?\" (o similar) y transfiere a
      RootAgent_v1. Ya no se involucra en la toma de pedido.

  - **OrderTakingAgent_v1 (OTA - Especialista en Pedidos con Menú
    PDF)**:

    - **Sin Saludo Inicial**: Asume que CMA ya saludó.

    - **Menú PDF como Flujo Primario**: Al activarse (o si el usuario
      pide el menú), llama a la herramienta solicitar_envio_menu_pdf. El
      script de Telegram enviará el PDF. OTA guía al usuario a
      seleccionar ítems del PDF (por código o nombre).

    - **Procesamiento de Pedido**: Usa manage_order_item para añadir
      selecciones. Mantiene la lógica para promociones
      (get_active_promotions) y preguntas específicas sobre
      ítems/categorías (get_item_details_by_name, get_items_by_category)
      como apoyo al PDF.

    - **Finalización**: Al terminar el usuario de añadir ítems, resume
      el pedido (sin subtotal detallado por ahora, solo ítems) y
      transfiere a RootAgent_v1.

    - **\"Escape Hatch\"**: Implementado para transferir a RootAgent_v1
      si la intención del usuario se desvía.

  - **DeliveryConfirmationAgent_v1 (DCA - Especialista en Entrega)**:

    - **Responsabilidad**: Confirmar los ítems del pedido (resumen de
      OTA), gestionar la dirección de envío (usando get_saved_addresses,
      register_update_customer para direcciones nuevas/actualizadas),
      calcular y presentar costos/tiempos de envío (usando
      calculate_delivery_cost).

    - **Llamadas a Herramientas Obligatorias**: Sus instructions se
      reforzarán para asegurar que llame a las herramientas mencionadas
      en los momentos precisos.

    - **Finalización**: Al confirmar todos los detalles de entrega,
      transfiere a RootAgent_v1 para la verificación final.

    - **\"Escape Hatch\"**: Implementado.

- **Prompts (Instructions) Concisos y Directos**: Un objetivo continuo
  es refinar todas las instructions para que sean claras, específicas y
  minimicen la ambigüedad para los LLM.

**2. Avances Recientes y Estado Actual (Desde la última actualización
proyecto adk google avance 3.0.docx)**

- **Entorno de Desarrollo en Mac mini**: Solucionados los problemas con
  la versión de Python y la instalación de pip en el entorno virtual
  (.venv), que ahora usa Python 3.11.

- **Integración con Telegram (telegram_pizzeria_bot.py)**:

  - El bot se conecta a Telegram y puede recibir mensajes y enviar
    respuestas.

  - Se ha implementado la estructura básica para manejar la interacción
    con el Runner de ADK.

  - Se ha añadido la lógica para que el script de Telegram envíe el
    menu_pizzeria.pdf cuando el OrderTakingAgent_v1 lo solicite.

- **Diseño Detallado de instructions (Enfoque 2.1)**:

  - Se han redactado versiones avanzadas de las instructions para:

    - CustomerManagementAgent_v1 (v3.0 - Enfoque 2.1): Con el nuevo
      flujo de saludo y pregunta final.

    - OrderTakingAgent_v1 (v8.0 - Enfoque PDF y sin saludo): Con la
      lógica del menú PDF.

    - RootAgent_v1 (v2.0 - Enfoque 2.1 Orquestador Central): Con la
      lógica de estados (current_main_goal, processing_order_sub_phase),
      detección de intención post-CMA, y orquestación de fases.

  - Está pendiente el refinamiento final de la instruction del
    DeliveryConfirmationAgent_v1 y la adición formal de \"escape
    hatches\" a todos los sub-agentes.

- **Nuevas Herramientas en pizzeria_tools.py**:

  - solicitar_envio_menu_pdf(): Para que OTA indique al script de
    Telegram que envíe el PDF.

  - update_session_flow_state(): Herramienta crucial para que
    RootAgent_v1 pueda modificar explícitamente current_main_goal y
    processing_order_sub_phase en session.state.

  - cancel_pending_order_tool(): Herramienta conceptual para que
    RootAgent_v1 maneje cancelaciones.

- **Pruebas Iniciales y Depuración (Conversación log3 de Telegram y
  log6/log7 de consola)**:

  - Se ha logrado un flujo de pedido completo en Telegram, desde el
    saludo hasta el registro del pedido.

  - Se identificó que RootAgent_v1 no estaba actualizando el estado
    (current_main_goal, processing_order_sub_phase) porque un LlmAgent
    no puede hacerlo solo con texto en su instruction -\> Solución
    propuesta: usar la herramienta update_session_flow_state.

  - Se observó que DeliveryConfirmationAgent_v1 a veces parecía omitir
    llamadas explícitas a herramientas como get_saved_addresses o
    register_update_customer, aunque el flujo final sugirió que de
    alguna manera la información correcta llegaba (posiblemente por el
    LLM tomando atajos o el log de consola no capturando todas las
    llamadas internas del agente). Se necesita reforzar sus
    instructions.

  - El OrderTakingAgent_v1 manejó bien la búsqueda por ingrediente
    después de la corrección de su PASO 7, pero mostró confusión con el
    \"Pack Amigos\" y un error genérico al intentar listar gaseosas
    (posiblemente por ReadTimeout o datos faltantes en Sheets).

  - Se detectó una advertencia en la herramienta
    registrar_pedido_finalizado sobre encabezados no coincidentes en la
    hoja \"Pedidos_Registrados\" de Google Sheets.

**3. Tareas Pendientes de Desarrollo (Corto Plazo - Próxima Iteración)**

**Implementar la Herramienta update_session_flow_state en
pizzeria_tools.py**: Ya te pasé el código para esto.

**Modificar la instruction del RootAgent_v1 para que LLAME a
update_session_flow_state** en todos los puntos donde se necesite
cambiar current_main_goal, processing_order_sub_phase, y manejar
pending_initial_query y \_current_order_items (para limpieza en
cancelaciones). (Esta es la **prioridad #1** para estabilizar el flujo).

**Refinar y Finalizar la instruction del DeliveryConfirmationAgent_v1
(v5.0 o superior)**:

- Asegurar que **OBLIGATORIAMENTE** llame a get_saved_addresses antes de
  presentar direcciones.

- Asegurar que **OBLIGATORIAMENTE** llame a register_update_customer
  después de que el usuario confirme una nueva dirección y **ANTES** de
  decir \"dirección guardada\".

- Asegurar que **OBLIGATORIAMENTE** llame a calculate_delivery_cost
  después de tener la dirección confirmada y **ANTES** de dar el costo
  de envío.

- Implementar su cláusula \"Escape Hatch\".

  **Añadir/Refinar Cláusulas \"Escape Hatch\" en
  CustomerManagementAgent_v1 y OrderTakingAgent_v1**: Para que
  transfieran al RootAgent_v1 si el input del usuario es inesperado o
  fuera de su alcance.

  **Refinar instruction del OrderTakingAgent_v1**:

- Para evitar la confusión con promociones no seleccionadas
  explícitamente (ej. el \"Pack Amigos\").

- Para mejorar el manejo de cuando el usuario pide listar ítems de una
  categoría (ej. \"muestrame las gaseosas\") y la herramienta falla o no
  encuentra nada.

  **Corregir Encabezados en Google Sheets**: El usuario (tú) debe
  asegurar que la pestaña \"Pedidos_Registrados\" tenga los encabezados
  exactos que espera la herramienta registrar_pedido_finalizado.

  **Verificar Datos de Menú en Google Sheets**: Asegurar que haya ítems
  en categorías como \"Bebidas\", \"Gaseosas\", \"Aguas\" y que estén
  marcados como disponibles, para evitar los status=\'not_found\' de
  get_items_by_category.

  **Monitorear ReadTimeout de Google Sheets**: Si persiste, investigar
  posibles soluciones (reintentos en sheets_client.py, verificar cuotas
  de API).

  **Pruebas Exhaustivas y Logs Sincronizados**: Realizar pruebas
  completas en Telegram y analizar los logs de consola y transcripts de
  Telegram juntos para depurar y refinar.

**4. Tareas Pendientes de Desarrollo (Largo Plazo / Futuras Mejoras)**

- **Implementar Lógica de \"Modificar Pedido\" y \"Cancelar Pedido
  Confirmado\"** a través del RootAgent_v1 y posiblemente un
  OrderModificationAgent.

- **Herramientas para RootAgent_v1 para Preguntas Generales**: Como
  get_store_info_tool (horarios, ubicación de la pizzería, etc.) o
  log_complaint_tool.

- **Manejo de Pago**: Diseñar e implementar PaymentProcessingAgent y
  herramientas asociadas.

- **Flujo de \"Aprobación de Cocina\" Completo**:

  - Integración con Telegram para enviar notificaciones a cocina.

  - Mecanismo para que cocina apruebe/rechace.

  - Agente para procesar esa respuesta y notificar al cliente.

- **Agentes Adicionales del Plan Original**: DailyReportAgent.

- **Persistencia de Sesión Robusta**: Cambiar de InMemorySessionService
  a DatabaseSessionService o VertexAiSessionService para que las
  conversaciones no se pierdan.

- **Optimización de Llamadas a LLM**: Una vez que el flujo sea estable,
  revisar si hay oportunidades para reducir llamadas innecesarias.

- **Mejoras en la Naturalidad del Lenguaje y Personalidad del Bot**.

- **Considerar Webhooks para Telegram**: Para una mayor eficiencia en
  producción en lugar de long polling.

**5. Conclusión de esta Actualización del Plan**

El proyecto ha entrado en una fase de refinamiento de la arquitectura de
agentes hacia un modelo más robusto y centrado en un RootAgent_v1
inteligente. Los problemas principales identificados (actualización de
estado por RootAgent_v1, y sub-agentes no llamando a herramientas
consistentemente) son los bloqueadores actuales. La introducción del
menú PDF y el manejo de intenciones más diversas por parte del
RootAgent_v1 son los siguientes grandes pasos funcionales.

La prioridad inmediata es estabilizar el flujo del \"Enfoque 2.1\"
asegurando que el RootAgent_v1 pueda gestionar el estado correctamente
(mediante la nueva herramienta update_session_flow_state) y que los
sub-agentes sigan sus instructions de manera más precisa, especialmente
en cuanto a las llamadas a herramientas y la gestión de los \"escape
hatches".

**Actualización del Plan de Desarrollo: PizzeríaBot (30 de Mayo, 2025)**

**1. Visión General y Enfoque Actual (Enfoque 2.1 - Orquestador Central
Inteligente)**

- **Reafirmación del Objetivo**: PizzeríaBot sigue siendo un chatbot
  inteligente para automatizar pedidos, integrado con Telegram (futuro)
  y usando Google Sheets como backend. El tono es \"Angelo de Pizzería
  San Marzano\", amigable, formal y eficiente.

- **Arquitectura de Agentes (Enfoque 2.1 - Orquestador Central
  Inteligente)**:

  - **RootAgent_v1 (Orquestador Principal)**: Sigue actuando como el
    principal oyente e intérprete de las intenciones del usuario. Ahora
    gestiona el Flow State explícitamente y es responsable de la
    orquestación de fases, el manejo de intenciones post-CMA y la
    gestión de \"Escape Hatch\". Ha mejorado significativamente la
    emisión de respuestas textuales en sus transiciones.

  - **CustomerManagementAgent_v1 (CMA - Experto en Clientes y Saludo
    Único)**: Responsabilidad única: siempre es el primer agente
    especializado en interactuar con el usuario para
    identificarlo/registrarlo y transferir a RootAgent_v1.

  - **OrderTakingAgent_v1 (OTA - Especialista en Pedidos con Menú
    PDF)**: Especialista en procesar pedidos, manejar ítems, categorías,
    promociones y ofrecer menú PDF. Se ha enfocado en mejorar la adición
    y modificación de ítems.

  - **DeliveryConfirmationAgent_v1 (DCA - Especialista en Entrega)**:
    Responsable de confirmar el pedido, gestionar la dirección de envío
    (guardar/actualizar), calcular y presentar costos/tiempos.

- **Prompts (Instructions) Concisos y Directos**: Un objetivo continuo
  es refinar todas las instructions para que sean claras, específicas y
  minimicen la ambigüedad para los LLM.

- **Modelo LLM:** Se ha actualizado a **Gemini 2.0**, lo que ha mejorado
  la capacidad de los agentes para seguir instrucciones complejas y
  razonar sobre el uso de herramientas.

**2. Logros y Avances Desde la Última Actualización (¡Progreso
Masivo!)**

Hemos alcanzado **hitos críticos** en la estabilización y funcionalidad
del bot, superando problemas complejos de orquestación y manejo de
datos:

- **pizzeria_agents.py Actualizado:**

  - **RootAgent_v1 (v2.3) - Orquestación Sólida y Respuestas Claras:**

    - **update_session_flow_state Integrado y Funcional:** El RootAgent
      ahora utiliza esta herramienta de forma explícita para gestionar
      current_main_goal y processing_order_sub_phase. Esto ha sido el
      **punto de inflexión** para la estabilidad del flujo.

    <!-- -->

    - **Verificación de Pedido Pendiente (check_pending_order):** El
      RootAgent ahora llama a esta nueva herramienta al inicio de una
      conversación y, si encuentra un pedido en curso del día, ofrece al
      cliente retomarlo o iniciar uno nuevo.

    - **Eliminación de Respuestas Silenciosas:** Las instructions del
      RootAgent han sido refinadas para asegurar que siempre haya una
      respuesta textual clara en las transiciones entre agentes o al
      finalizar una fase, mejorando la experiencia de usuario.

  - **CustomerManagementAgent_v1 (v3.1) - Registro Robusto:**

    - Funcional y estable en el saludo, identificación y registro de
      clientes. Transfiere correctamente al RootAgent.

  - **OrderTakingAgent_v1 (v8.3) - Gestión de Pedidos Avanzada:**

    - **Manejo de Clarificación por Ambüedad de Nombres (ej., \"pizza
      americana\"):** El bot ahora pide clarificación explícita si el
      nombre es ambiguo, listando opciones.

    - **Manejo de \"Ítem No Encontrado\":** Se han mejorado las
      sugerencias al usuario (revisar PDF, buscar por ingrediente).

    - **Flujo \"Es Todo\":** El mensaje de finalización ha sido refinado
      para una transición fluida al DeliveryConfirmationAgent_v1.

  - **DeliveryConfirmationAgent_v1 (v5.3) - Confirmación de Entrega
    Inteligente:**

    - **Ofrecimiento de Direcciones Guardadas:** El DCA ahora detecta y
      ofrece explícitamente las direcciones guardadas (principal y
      secundaria) al cliente.

    - **Muestra Resumen Completo del Pedido:** Antes de la confirmación
      final, el bot presenta un resumen detallado que incluye ítems,
      subtotal, dirección de envío, costo de envío y total a pagar.

- **pizzeria_tools.py Actualizado:**

  - **Herramientas Asíncronas y No Bloqueantes:** Todas las herramientas
    que interactúan con Google Sheets (get_customer_data,
    register_update_customer, etc.) son ahora async def y utilizan
    asyncio.get_event_loop().run_in_executor() para no bloquear el bucle
    de eventos. **Esto resolvió el problema de \"bot colgado\".**

  - **Registro Robusto de ID de Cliente:** register_update_customer
    asegura que el ID_Cliente se registre correctamente como texto plano
    (str()) y utiliza value_input_option=\'RAW\' para evitar corrupción
    de datos en Google Sheets.

  - **Manejo Correcto de Estado None:** Las herramientas ahora manejan
    correctamente los valores None en el estado de la sesión, evitando
    TypeErrors.

  <!-- -->

  - **check_pending_order Implementado:** Nueva herramienta para
    verificar pedidos pendientes en Google Sheets.

  <!-- -->

  - **Coherencia de Encabezados:** La herramienta
    registrar_pedido_finalizado ahora está perfectamente alineada con
    los encabezados de la hoja \"Pedidos_Registrados\" que acordamos,
    eliminando la advertencia de inconsistencia.

- **sheets_client.py:** Mantiene su funcionalidad de acceso a Google
  Sheets.

- **telegram_pizzeria_bot.py:** Funciona como la capa de interfaz,
  orquestando las interacciones con el Runner de ADK.

**3. Estado Actual y Dificultades (¡Ya son Refinamientos Finos!)**

El proyecto ha alcanzado una **estabilidad y funcionalidad muy altas**
para el flujo principal de toma de pedidos. Los problemas restantes son
mayormente refinamientos para casos de uso específicos y la mejora de la
experiencia de usuario:

- **1. OrderTakingAgent_v1 (OTA) - Lógica de Reemplazo/Modificación de
  Ítems (Prioridad Alta):**

  - **Problema:** Cuando el usuario quiere \"cambiar\" o \"reemplazar\"
    un ítem ya en el pedido (ej., de \"Grande\" a \"Familiar\"), el OTA
    tiende a añadir el nuevo ítem y luego preguntar si se desea eliminar
    el anterior. No realiza un reemplazo directo.

  - **Cómo se está afrontando:** La instruction de OTA (PASO 5.b) ya
    incluye la lógica para detectar la intención de \"cambiar\" y
    realizar remove + add. Necesitamos probar esto y, si el LLM no lo
    sigue consistentemente, ajustar la instruction para que sea aún más
    imperativa o dar ejemplos más claros.

- **2. OrderTakingAgent_v1 (OTA) - Manejo de \"la más pequeña/grande\"
  (Nombres Contradictorios) (Prioridad Media):**

  - **Problema:** Aunque la instruction de OTA pide clarificación
    explícita de tamaño (\"¿Cuál prefieres?\"), el LLM aún puede tener
    dificultades con nombres de ítems que son contradictorios (ej.,
    \"Pizza Grande\" es más pequeña en precio que \"Pizza Familiar\").
    Esto puede llevar a que el LLM elija el tamaño incorrecto si el
    usuario no especifica el nombre exacto.

  - **Cómo se está afrontando:** La instruction ya contiene la directriz
    de pedir el \"nombre exacto del tamaño o ID\". La prueba determinará
    si es suficiente.

- **3. RootAgent_v1 - Lógica de Prioridad de check_pending_order y
  Limpieza de pending_initial_query (Prioridad Media):**

  - **Problema:** Cuando un usuario con un pedido pendiente inicia una
    *nueva* interacción (\"hola\"), el RootAgent detecta el pedido
    pendiente pero puede priorizar la lógica de \"iniciar nuevo pedido\"
    (pasando el \"hola\" a CMA) en lugar de ofrecer inmediatamente las
    opciones para el pedido pendiente, llevando a un inicio de
    conversación ligeramente confuso. Además, el pending_initial_query
    de la nueva frase no se limpia si el flujo se desvía a la gestión de
    pedido pendiente.

  - **Cómo se está afrontando:** Necesitamos ajustar la instruction del
    RootAgent para que la rama de \"pedido pendiente\" tenga la máxima
    prioridad si check_pending_order devuelve pending_order, y para que
    limpie pending_initial_query si el flujo cambia de una \"nueva
    consulta\" a la gestión de un \"pedido pendiente\".

- **4. DeliveryConfirmationAgent_v1 (DCA) - Manejo de Dirección
  Secundaria (Caso de Prueba Específico) (Prioridad Baja):**

  - **Problema:** La instruction de DCA ya tiene lógica para manejar
    direcciones secundarias, pero este flujo aún no ha sido probado
    interactivamente en el log.

  - **Cómo se está afrontando:** Necesitamos una prueba explícita para
    validar este escenario.

**4. Lo que Falta y Próximos Pasos (Hoja de Ruta)**

Con la estabilidad actual, podemos enfocarnos en:

**Validar los refinamientos existentes con pruebas exhaustivas (los
puntos 1, 2, 3 y 4 de \"Problemas Pendientes\" de arriba).**

**Implementar el envío real del menú PDF en telegram_pizzeria_bot.py:**
La herramienta solicitar_envio_menu_pdf ya señaliza la acción, pero la
parte de Telegram de enviar el archivo real aún está pendiente.

**Refinar la Lógica de \"Escape Hatch\" de Agentes:** Aunque
implementados, seguir monitoreando si los agentes transfieren
correctamente al RootAgent cuando la intención del usuario es claramente
fuera de su alcance.

**Integración y Prueba con Telegram (Completa):** Migrar del chat de
consola a pruebas en Telegram para un entorno más realista.

**Persistencia de Sesión Real:** Migrar de InMemorySessionService a
DatabaseSessionService o VertexAiSessionService para asegurar que las
conversaciones no se pierdan al reiniciar el bot.

**Desarrollo de Agentes Pendientes (Fase Futura):**
PaymentConfirmationAgent, DailyReportAgent, KitchenApprovalAgent.


Actualización del Plan de Desarrollo: PizzeríaBot (04 de Junio, 2025)

1. Visión General y Enfoque Actual (Enfoque 2.1 - Orquestador Central Inteligente)

Reafirmación del Objetivo: PizzeríaBot sigue siendo un chatbot inteligente para automatizar pedidos, integrado con Telegram y usando Google Sheets como backend. El tono es "Angelo de Pizzería San Marzano", amigable, formal y eficiente.
Evolución de la Arquitectura de Agentes (Enfoque 2.1 - Orquestador Central Inteligente):
RootAgent_v1 (RA - Orquestador Principal): Actúa como el principal oyente e intérprete de las intenciones del usuario en casi todos los turnos. Gestiona el Flow State explícitamente (current_main_goal, processing_order_sub_phase) para rastrear el objetivo general y la sub-fase actual de la conversación. Delega fases completas de la interacción a agentes especializados y maneja "escape hatches" cuando un sub-agente no entiende la intención o hay un error. Responde directamente al usuario solo en casos de clarificación o errores irrecuperables.
CustomerManagementAgent_v1 (CMA - Experto en Clientes y Saludo): Es siempre el primer agente especializado en interactuar con el usuario (después de la derivación inicial del RA). Su rol es identificar/registrar al cliente y saludarlo apropiadamente. Ya NO transfiere el control al RootAgent_v1 inmediatamente después de su saludo o registro, sino que mantiene el control y espera la siguiente interacción del usuario. Solo transfiere al RA en caso de "escape hatch".
OrderTakingAgent_v1 (OTA - Especialista en Pedidos con Menú PDF): Se encarga de procesar pedidos, manejar ítems, categorías, promociones y ofrecer el menú PDF. Ya NO incluye la frase "Un momento..." al inicio de su procesamiento de pedido, buscando mayor agilidad. Devuelve el control al RA cuando su ciclo de toma de pedidos ha terminado con éxito, cuando no percibe claramente la intención del usuario, o cuando ocurre un error que no puede manejar.
DeliveryConfirmationAgent_v1 (DCA - Especialista en Entrega): Responsable de confirmar los ítems del pedido, gestionar la dirección de envío (guardar/actualizar), y presentar el resumen final. El cálculo automático del costo de envío ha sido postergado y eliminado de su flujo actual. Ahora informa al usuario que el costo de envío será calculado por el personal. Devuelve el control al RA en los casos previstos.
Prompts (Instructions) Concisos y Directos: Un objetivo continuo es refinar todas las instructions para que sean claras, específicas y minimicen la ambigüedad para los LLM.
Modelo LLM: Se utiliza gemini-2.0-flash como modelo principal, garantizando la capacidad de "instruction following" necesaria para la complejidad del bot.
Integración con Telegram: El bot se integra con Telegram como interfaz de usuario, manejando los mensajes, el envío de PDFs y la comunicación de las respuestas de los agentes.
2. Logros y Avances Detallados Hasta la Fecha

Hemos alcanzado hitos críticos en la estabilidad y funcionalidad del bot, logrando que el flujo principal de pedido se ejecute de forma coherente y robusta.

2.1. Agentes Implementados y Funcionales (Estado Actualizado):

CustomerManagementAgent_v1 (CMA v3.4):

Estado: ✅ Altamente Funcional y Estable.
Logros:
Saluda a los usuarios y verifica su existencia (get_customer_data).
Personaliza el saludo para clientes recurrentes y solicita nombre a nuevos clientes.
Registra/actualiza clientes (register_update_customer).
CRÍTICO RESUELTO: Ya NO transfiere el control al RootAgent_v1 inmediatamente después de su saludo o registro. Mantiene el control y espera la siguiente interacción del usuario, transfiriendo al RA solo si la intención del usuario está fuera de su alcance.
Maneja graciosamente errores de base de datos en get_customer_data.
Herramientas: get_customer_data, register_update_customer.
OrderTakingAgent_v1 (OTA v8.4):

Estado: ✅ Altamente Funcional y Estable.
Logros:
Procesa pedidos iniciales y solicitudes de menú PDF (solicitar_envio_menu_pdf funciona enviando el PDF real vía Telegram).
Añade, actualiza y remueve ítems (manage_order_item).
Maneja la ambigüedad de ítems (ej. diferentes tamaños de pizza), pidiendo clarificación explícita y usando el nombre exacto/ID para la herramienta.
Maneja ítems no encontrados con sugerencias mejoradas.
Confirma ítems añadidos y muestra resumen de pedido (view_current_order).
CRÍTICO RESUELTO: Ya NO incluye la frase "Un momento..." al inicio de su procesamiento de pedido, haciendo el flujo más ágil.
Herramientas: solicitar_envio_menu_pdf, get_items_by_category, get_item_details_by_name, get_active_promotions, manage_order_item, view_current_order, update_session_flow_state.
DeliveryConfirmationAgent_v1 (DCA v5.5):

Estado: ✅ Funcional para el flujo sin cálculo de delivery.
Logros:
Inicia correctamente, confirmando el pedido y gestionando la dirección de envío.
Llama a get_saved_addresses y ofrece direcciones guardadas o pide una nueva.
Registra/actualiza direcciones (register_update_customer).
CRÍTICO RESUELTO: El KeyError: 'Context variable not found: direccion_potencial' ha sido solucionado al eliminar referencias a variables internas del LLM en la instrucción.
CRÍTICO RESUELTO: El KeyError: 'Context variable not found: delivery_time_estimate' ha sido solucionado al asegurar que la herramienta calculate_delivery_cost guarda este valor en el estado, y la instrucción del DCA lo referencia correctamente desde allí.
NUEVO FLUJO DE DELIVERY: Ya NO llama a calculate_delivery_cost directamente en su flujo principal. En su lugar, informa al usuario que "El costo de envío será calculado por un personal de la pizzería y se te comunicará en breve" en el resumen final.
Transfiere el control al RootAgent_v1 para la verificación final y registro del pedido.
Herramientas: view_current_order, get_saved_addresses, register_update_customer. (Nota: calculate_delivery_cost se mantiene importada en pizzeria_agents.py pero ya no se usa en el DCA).
RootAgent_v1 (RA v2.7 - Orquestador Principal):

Estado: ✅ Altamente Funcional para Orquestación Central.
Logros:
Maneja el inicio de la conversación y transfiere correctamente al CustomerManagementAgent_v1.
CRÍTICO RESUELTO: Ha sido instruido para clasificar el pending_initial_query (incluso si es solo un saludo) y tomar la iniciativa de preguntar proactivamente al usuario ("¡Excelente! ¿Qué te apetece pedir hoy?").
Transfiere correctamente entre CustomerManagementAgent_v1, OrderTakingAgent_v1 y DeliveryConfirmationAgent_v1 basado en las fases del pedido (current_main_goal, processing_order_sub_phase).
Realiza la verificación final del cliente y del pedido antes del registro.
Registra pedidos finalizados en Google Sheets con el estado "Pendiente Aprobación Personal" (registrar_pedido_finalizado).
Emite el mensaje final de confirmación del pedido ("Gracias por preferirnos. Tu pedido se envió al administrador para su aprobación. En breve nos comunicaremos contigo.").
Maneja agradecimientos y finalizaciones de conversación, reiniciando el estado.
Sus "escape hatches" generales permiten reencaminar flujos inesperados o manejar errores no específicos de los sub-agentes, respondiendo al usuario en caso de ambigüedad o problemas internos.
Herramientas: update_session_flow_state, get_customer_data, view_current_order, registrar_pedido_finalizado, cancel_pending_order_tool, check_pending_order.
2.2. Herramientas (pizzeria_tools.py) (Estado Actualizado):

Todas las herramientas son asíncronas y manejan la base de datos de Google Sheets (sheets_client.py).

get_customer_data: ✅ Funcional.
register_update_customer: ✅ Funcional.
get_items_by_category: ✅ Funcional.
get_item_details_by_name: ✅ Funcional (maneja ambigüedad y ítems no encontrados).
get_active_promotions: ✅ Funcional.
manage_order_item: ✅ Funcional (añadir, actualizar, remover, integrar con get_item_details_by_name para validación y resolución de ambigüedad).
view_current_order: ✅ Funcional.
get_saved_addresses: ✅ Funcional.
calculate_delivery_cost: ✅ Funcional, pero ya NO utilizada directamente en el flujo del DeliveryConfirmationAgent_v1 en este momento. Se mantiene en el código para futura implementación del cálculo automático.
registrar_pedido_finalizado: ✅ Funcional. Se corrigió el orden de argumentos. Ahora registra pedidos con costo de envío y total en 0.0 y estado "Pendiente Aprobación Personal".
solicitar_envio_menu_pdf: ✅ Funcional (señaliza la acción al bot de Telegram).
update_session_flow_state: ✅ Funcional.
cancel_pending_order_tool: ✅ Funcional.
check_pending_order: ✅ Funcional.
2.3. Infraestructura y Lógica General (Estado Actualizado):

Manejo de _session_user_id: Implementado robustamente a través del focused_set_user_id_callback, asegurando el contexto correcto del usuario.
Estructura Multi-Agente con Transferencia: El concepto de transferir el control entre agentes es ahora sólido y predecible, con cada agente cumpliendo su ciclo y el RootAgent orquestando las transiciones y excepciones.
Logging Mejorado: La verbosidad de logs internos de ADK y httpx/gspread ha sido reducida para una depuración más limpia.
Integración con Telegram (telegram_pizzeria_bot.py):
La comunicación con la API de Telegram ha sido estabilizada (problemas de Timeout mitigados con un DEFAULT_HTTPX_TIMEOUT más largo).
El envío del menú PDF funciona correctamente.
La captura y emisión de respuestas textuales de los agentes (incluyendo sub-agentes) es robusta.
CRÍTICO RESUELTO: El error TypeError: Request.__init__() got an unexpected keyword argument 'timeout' ha sido solucionado.
CRÍTICO RESUELTO: El ImportError: cannot import name 'str' from 'typing' ha sido solucionado.
3. Estado Actual y Desafíos Restantes

El proyecto PizzeríaBot ha alcanzado un estado de alta funcionalidad y estabilidad para el flujo completo del "camino feliz" de un pedido, desde el saludo hasta el registro final en la base de datos (Google Sheets).

3.1. Problemas Pendientes de Lógica / Refinamiento (No Bloqueantes para el Flujo Principal):

DCA - Redundancia en Confirmación de Dirección (Prioridad Media):

Problema: El DeliveryConfirmationAgent_v1 a veces pide la confirmación de la dirección de envío de forma un poco redundante ("Gracias. He recibido la dirección que me indicaste. ¿Es correcta?" y luego "¿Deseas usar tu dirección principal...?") después de que el usuario ya ha proporcionado o elegido una dirección.
Acción: Ajustar la instrucción del DCA (PASO 3.c) para que sea más concisa y directa al confirmar la dirección o al ofrecer las opciones guardadas.
OTA - Lógica de "la más pequeña/grande" (Prioridad Media):

Problema: Aunque la instrucción del OTA pide clarificación explícita de tamaño ("¿Cuál prefieres?"), el LLM aún puede tener dificultades con nombres de ítems que son contradictorios (ej., "Pizza Grande" es más pequeña en precio que "Pizza Familiar") o al procesar "la más grande/pequeña". Esto puede llevar a que el LLM elija el tamaño incorrecto si el usuario no especifica el nombre exacto.
Acción: Monitorear este comportamiento. Si persiste, ajustar la instrucción del OTA (PASO 5.b.vi) para que sea aún más imperativa en solicitar el nombre exacto o el ID del plato.
RootAgent - Manejo de pending_initial_query cuando es un saludo (Prioridad Baja):

Problema: Aunque el RA ya toma la iniciativa de preguntar proactivamente, el pending_initial_query aún puede contener un saludo que, si se clasifica mal, podría ser pasado al OTA, causando una pequeña confusión.
Acción: Refinar el PASO 0.A del RootAgent_v1 para que, si el mensaje inicial es solo un saludo, pending_initial_query se establezca explícitamente a None o una cadena vacía.
4. Lo que Falta y Próximos Pasos (Hoja de Ruta)

Con el "camino feliz" principal funcionando sólidamente, los próximos pasos son:

Finalizar el Refinamiento de Instrucciones (Puntos 3.1): Aplicar los ajustes finos en las instrucciones del DCA, OTA y RA.
Implementar el Sistema de Aviso de Fallos para el RA (Prioridad Alta - Próxima Iteración):
Razón: Para que el RA pueda ser un supervisor proactivo, necesitamos que los sub-agentes reporten fallos específicos al estado de la sesión (ej. _error_dca_sin_direcciones_encontradas).
Acción: Implementar las variables de estado de fallo en las herramientas/sub-agentes y la lógica de detección y reencaminamiento/respuesta en el RootAgent_v1.
Integración con Personal (Personal de Pizzería):
Notificación al Personal: Implementar la funcionalidad para que, al registrar el pedido finalizado (estado "Pendiente Aprobación Personal"), se envíe una notificación a un canal de Telegram/WhatsApp del personal de la pizzería con los detalles del pedido, la dirección y la nota de que el costo de envío es pendiente.
Aprobación/Rechazo del Personal: Diseñar un mecanismo para que el personal pueda aprobar o rechazar el pedido (quizás respondiendo a la notificación con un comando o un formato específico) y proporcionar el costo de envío en esa respuesta.
Actualización del Estado y Notificación al Cliente: Implementar una herramienta y lógica en el RA para procesar la respuesta del personal, actualizar el estado del pedido en Google Sheets (ej. a "Aprobado, En Preparación" y rellenar Costo_Envio y Total_Pedido), y notificar proactivamente al cliente el nuevo estado y el costo de envío final.
Desarrollo de Agentes Pendientes (Fase Futura):
PaymentConfirmationAgent (si se decide implementar pagos en línea).
DailyReportAgent.
Persistencia de Sesión Real: Migrar de InMemorySessionService a DatabaseSessionService o VertexAiSessionService para asegurar que las conversaciones no se pierdan al reiniciar el bot.
5. Conclusión General:

El proyecto PizzeríaBot ha demostrado una progresión excepcional. Hemos superado desafíos complejos de orquestación, manejo de datos y problemas técnicos, logrando un flujo conversacional funcional y coherente a través de los tres agentes principales. El "camino feliz" está validado hasta el registro del pedido con la aprobación del personal. La estrategia de depuración iterativa y el refinamiento de las instrucciones han sido fundamentales para este éxito. Estamos bien posicionados para construir sobre esta base y añadir las funcionalidades restantes.



Actualizacion Estado del Proyecto: PizzeríaBot (05 de Junio, 2025)
1. Descripción General del Proyecto
PizzeríaBot es un sistema de chatbot inteligente diseñado para automatizar y mejorar la experiencia de toma de pedidos para una pizzería. El proyecto se está desarrollando en Python utilizando el Agent Development Kit (ADK) de Google, con el objetivo de integrarse con plataformas de mensajería como Telegram. La gestión de datos (menú, clientes, pedidos) se realiza a través de Google Sheets. El tono de comunicación del bot se define como amigable, proactivo, directo y formal, encarnado por "Angelo de Pizzería San Marzano".

El sistema se basa en una arquitectura multi-agente centralizada, donde un RootAgent orquesta el flujo entre agentes especializados, cada uno con un rol claro:

Gestión de Clientes (CustomerManagementAgent_v1): Saludo, identificación y registro de clientes.
Toma de Pedidos (OrderTakingAgent_v1): Navegación de menú (con soporte PDF), adición/modificación/eliminación de ítems, y gestión de promociones.
Confirmación de Entrega (DeliveryConfirmationAgent_v1): Confirmación de pedido, gestión de dirección de envío y resumen final.
(Futuro) Procesamiento Final y Pago: Confirmación de pago y procesamiento final del pedido.
Enfoque Actual (Orquestador Central Inteligente): El RootAgent_v1 actúa como el oyente e intérprete principal de las intenciones del usuario en casi todos los turnos. Utiliza variables en session.state (como current_main_goal y processing_order_sub_phase) para rastrear el objetivo general y la sub-fase actual de la conversación, delegando fases completas de la interacción a los agentes especializados y manejando los "escape hatches".

2. Logros y Avances Hasta la Fecha
Hemos alcanzado hitos críticos en el desarrollo y depuración de los componentes centrales del sistema, logrando un flujo conversacional coherente y funcional para el "camino feliz" de un nuevo cliente que realiza un pedido.

2.1. Agentes Implementados y Funcionales:

CustomerManagementAgent_v1 (CMA v3.4):

Estado: ✅ Altamente Funcional y Estable.
Logros: Saluda y verifica clientes (get_customer_data), personaliza saludos, registra/actualiza clientes (register_update_customer), y mantiene el control esperando la respuesta del usuario antes de transferir al RootAgent (solo transfiere en caso de escape hatch).
Mejoras: Se refinó su instruction para asegurar un orden estricto de operaciones y evitar llamadas prematuras a herramientas.
OrderTakingAgent_v1 (OTA v8.4):

Estado: ✅ Altamente Funcional y Estable.
Logros: Procesa el pedido inicial del usuario, utiliza manage_order_item con todos los parámetros, maneja ambigüedad y ítems no encontrados con sugerencias mejoradas, confirma ítems añadidos, y maneja la finalización del pedido. Proporciona un mensaje de finalización exacto para una transición limpia. Ya no incluye la frase "Un momento..." al inicio de su procesamiento.
Mejoras: instruction refinada para forzar la llamada inmediata a manage_order_item y asegurar una respuesta conversacional post-herramienta.
DeliveryConfirmationAgent_v1 (DCA v5.5):

Estado: ✅ Funcional para el "Camino Feliz" (sin cálculo de delivery automático).
Logros: Confirma el pedido, gestiona la dirección de envío (ofreciendo guardadas o pidiendo nuevas), y usa register_update_customer. El KeyError de direccion_potencial y delivery_time_estimate fue solucionado.
Nuevo Flujo: Ya NO llama a calculate_delivery_cost directamente. En su lugar, informa al usuario que el costo de envío será calculado por el personal.
RootAgent_v1 (RA v2.7 - Orquestador Principal):

Estado: ✅ Altamente Funcional para Orquestación Central.
Logros: Maneja el inicio de conversación, transfiere correctamente entre CMA, OTA y DCA basado en las fases del pedido (current_main_goal, processing_order_sub_phase). Realiza la verificación final del cliente y del pedido, y registra pedidos finalizados en Google Sheets (registrar_pedido_finalizado). Ha mejorado la emisión de respuestas textuales en sus transiciones.
Nueva Lógica: Implementa check_pending_order al inicio de una conversación y, si encuentra un pedido en curso, ofrece al cliente retomarlo.
Herramienta Clave: Utiliza update_session_flow_state de forma explícita para gestionar los estados de flujo, lo que ha sido un punto de inflexión para la estabilidad del flujo.
2.2. Herramientas (pizzeria_tools.py) (Todas Asíncronas):

Todas las herramientas que interactúan con Google Sheets (get_customer_data, register_update_customer, etc.) son ahora async def y utilizan asyncio.get_event_loop().run_in_executor() para no bloquear el bucle de eventos, resolviendo el problema de "bot colgado".
register_update_customer asegura el registro robusto de ID_Cliente como texto plano (str()) y usa value_input_option='RAW'.
get_item_details_by_name fue mejorada para búsqueda flexible y manejo de ambigüedad.
manage_order_item es más robusta (parámetro instrucciones_especiales con valor por defecto).
registrar_pedido_finalizado está perfectamente alineada con los encabezados de la hoja Pedidos_Registrados, eliminando advertencias.
2.3. Infraestructura y Lógica General:

ADK Core: Uso de gemini-2.0-flash como modelo principal, configurado con max_output_tokens=8192.
Telegram Integration (telegram_pizzeria_bot.py): Estabilizada la comunicación con la API de Telegram. El envío de PDF funciona. Se solucionaron TypeError: Request.__init__() got an unexpected keyword argument 'timeout' e ImportError: cannot import name 'str' from 'typing'.
Logging Mejorado: Reducida la verbosidad de logs internos de ADK LLM y httpx/gspread para una depuración más limpia.
3. Desafíos Inmediatos y Nuevos Descubrimientos (Reenfoque)
A pesar de los grandes avances, las pruebas con el log2 revelaron desafíos críticos que requieren un reenfoque prioritario:

3.1. Problemas de Cuota/Disponibilidad del Modelo (Errores 429/503):

Problema: google.genai.errors.ServerError: 503 UNAVAILABLE y google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED causan la interrupción total de la conversación y frustración del usuario. Esto indica que la cuota de la API gratuita de Gemini se está excediendo o el modelo está sobrecargado.
Reenfoque / Solución Nueva: Implementar lógica de reintentos y "falla suave" con before_model_callback.
Este callback (adjunto al RootAgent) detectará estos errores, gestionará un contador de fallos en session.state, y en lugar de que la llamada al LLM falle, el callback intentará un reintento con backoff exponencial (asyncio.sleep) o, si los reintentos fallan, retornará un LlmResponse predefinido con un mensaje amigable al usuario (ej. "Angelo está ocupado...") para evitar el colapso.
Acción Inmediata: Prioridad 1 para la implementación.
3.2. Inconsistencia del Estado Global (current_main_goal):

Problema: A menudo, el log final del turno muestra MainGoal: IDLE y SubPhase: ESPERANDO_INPUT_POST_CMA o None, incluso cuando el RootAgent debería estar en PROCESANDO_PEDIDO. Esto indica que el estado no se mantiene persistentemente o se sobrescribe inadvertidamente.
Reenfoque / Solución Nueva: Ajustar la instruction del RootAgent_v1 para asegurar la persistencia del estado current_main_goal. La documentación de EventActions.state_delta y ToolContext.state confirma que las actualizaciones de estado son rastreadas y persistidas.
Acción: Revisar el PASO 0.A y 0.B.1 de la instruction del RootAgent_v1 para asegurar que current_main_goal='PROCESANDO_PEDIDO' se establezca de forma inmutable al inicio del flujo y solo se modifique a IDLE en puntos de finalización explícitos (pedido finalizado, cancelado, o escape hatch que termina el pedido).
3.3. Comportamiento Errático y Confusión de Nombres/Direcciones:

Problema: El bot confunde inputs (ej. "Oi que" o "Fabio Alessandro") con nombres o direcciones, o maneja mal los insultos, lo que rompe el flujo.
Reenfoque / Solución Nueva: Implementar validación robusta con before_tool_callback y refinar la instruction del RootAgent_v1 para el manejo de frustración.
Validación con before_tool_callback: Un before_tool_callback (adjunto a register_update_customer o a los agentes CMA/DCA) interceptará la llamada a la herramienta. Si los argumentos (Nombre_Completo, Direccion_Principal) son inválidos (ej., insultos, inputs sin sentido), el callback retornará un diccionario de error (ej., {"status": "validation_error"}) impidiendo la ejecución de la herramienta y guiando al agente a pedir una aclaración.
Manejo de Lenguaje Inapropiado (instruction del RA): En el PASO 2 del RootAgent_v1, añadir una condición explícita para detectar lenguaje ofensivo (😡😡😡, Burra). Si se detecta, el RootAgent responderá con un mensaje de calma, limpiará el estado corrompido (_customer_name_for_greeting, _last_confirmed_delivery_address_for_order), y reencaminará el flujo.
3.4. Respuestas Silenciosas/Genéricas del RootAgent:

Problema: El RootAgent_v1 a veces no genera una respuesta textual clara antes de transferir, llevando a mensajes por defecto del bot de Telegram.
Reenfoque / Solución Nueva: Asegurar que todas las transiciones del RootAgent_v1 culminen en una respuesta textual explícita.
Acción: Revisar cada transfer_to_agent en la instruction del RootAgent_v1 y garantizar que esté precedido por una respuesta al usuario, especialmente en PASO 0.B.2.i.
3.5. Precisión en las Preguntas del Agente del Menú (OTA):

Problema: El OTA falla en encontrar ítems si el nombre no es exacto, lo que lleva a un ciclo de "no encontrado".
Reenfoque / Solución Nueva: Refinar la instruction del OTA para guiar mejor al LLM.
Acción: En el PASO 5.b.vi.2 de la instruction del OrderTakingAgent_v1, enfatizar que el OTA debe siempre pedir el nombre exacto o el ID del menú PDF cuando get_item_details_by_name retorne clarification_needed o not_found, evitando adivinar o entrar en ciclos.
4. Objetivos a Mediano y Largo Plazo
4.1. Mediano Plazo (Próximas Iteraciones):

Implementar el Sistema de Aviso de Fallos para el RA: Los sub-agentes reportarán fallos específicos al estado de la sesión (ej. _error_dca_sin_direcciones_encontradas) y el RootAgent detectará y reencaminará/responderá.
Refinamiento Proactivo del DeliveryConfirmationAgent_v1: Mejorar su robustez para manejar casos donde el usuario proporcione la dirección en el mismo mensaje que confirma el pedido.
Manejo de Múltiples Ítems y Negativos en un Solo Input (OTA): Refinar la instruction del OTA para validar todos los ítems en un input múltiple y reportar problemas de una vez.
Lógica de Reemplazo/Modificación de Ítems (OTA): Probar a fondo el PASO 5.b de la instruction del OTA para el reemplazo explícito de ítems.
Integración y Prueba con Telegram (Completa): Tras estabilizar el flujo, migrar a pruebas exhaustivas en Telegram para un entorno más realista.
4.2. Largo Plazo (Fase de Escalabilidad y Expansión):

Persistencia de Sesión Real: Migrar de InMemorySessionService a VertexAiSessionService para asegurar que las conversaciones no se pierdan al reiniciar el bot, crucial para producción.
Integración con Sistemas de Restaurante (POS/CRM): Utilizar Google Cloud Tools como ApplicationIntegrationToolset para conectar con sistemas empresariales (Square, Salesforce, SAP) y Toolbox Tools for Databases para bases de datos reales.
Flujo de "Aprobación de Cocina" Completo: Implementar la notificación al personal vía Telegram/WhatsApp, un mecanismo de aprobación/rechazo, y la actualización del estado del pedido/notificación al cliente.
Desarrollo de Agentes Pendientes: PaymentConfirmationAgent, DailyReportAgent, KitchenApprovalAgent.
Capacidades Multimodales (Voz): Explorar el Streaming Integrado de ADK para pedidos telefónicos.
Evaluación Continua: Implementar el marco de evaluación de ADK (.test.json, evalsets) para medir tool_trajectory_avg_score y response_match_score y asegurar la calidad a largo plazo.

Estado del Proyecto: PizzeríaBot
Fecha: 15 de Junio, 2025
Versión: 1.0 (Versión de Lanzamiento)
Estado: Desarrollo del Núcleo Completado; Listo para Fase de Producción.
1. Resumen Ejecutivo
El proyecto PizzeríaBot ha culminado exitosamente su fase de desarrollo y depuración. Hemos transformado un prototipo inicial propenso a fallos en un sistema multi-agente robusto, funcional y escalable, utilizando el Agent Development Kit (ADK) de Google. La arquitectura final se basa en un orquestador central determinista que gestiona un equipo de agentes especialistas, garantizando un flujo de conversación predecible y fiable.

El bot es ahora capaz de gestionar una conversación completa, desde el saludo y registro del cliente, pasando por la toma de un pedido complejo, hasta la confirmación de la dirección y el registro final del pedido en una base de datos de Google Sheets.

Este documento detalla la evolución arquitectónica, el estado funcional de cada componente y los próximos pasos recomendados para llevar el proyecto a producción.

2. La Evolución Arquitectónica: El Cambio de Paradigma
Para entender el éxito del sistema actual, es crucial recordar la evolución desde nuestro punto de partida.

2.1. El Enfoque Inicial (Orquestación por LLM)

Nuestra primera versión se basaba en un RootAgent que también era un LlmAgent. La orquestación del flujo (decidir a qué especialista llamar y cuándo) dependía de una instruction muy larga y compleja que el LLM debía interpretar.

Debilidades:
Impredecible: El flujo podía variar, saltándose pasos o entrando en bucles.
Frágil: Cualquier cambio en el prompt del RootAgent corría el riesgo de romper toda la lógica.
Difícil de Depurar: Era casi imposible saber por qué el LLM tomaba una decisión incorrecta.
2.2. El Enfoque Final (Orquestación por Código - CustomAgent)

La arquitectura actual es significativamente más robusta. El RootOrchestratorAgent ya no es un LlmAgent, sino un CustomAgent que hereda de BaseAgent.

Fortalezas y Funcionamiento:
Flujo Determinista: La lógica de enrutamiento reside en código Python (if/elif) dentro del método _run_async_impl. El orquestador lee la variable de estado processing_order_sub_phase y ejecuta al especialista correspondiente. Es 100% predecible.
Agentes Especialistas: Los agentes (CustomerManagementAgent, OrderTakingAgent, etc.) son ahora LlmAgent más simples, con instructions cortas y enfocadas únicamente en su tarea.
Transiciones Claras: Los especialistas ya no se preocupan por el flujo general. Al terminar su tarea, llaman a la herramienta update_session_flow_state, que actúa como una "campanada" para que el RootAgent, en el siguiente turno, sepa que debe pasar a la siguiente fase.
Este cambio de paradigma de una orquestación basada en la interpretación de un LLM a una basada en código determinista es la mejora más importante que hemos implementado y la razón de la estabilidad actual del bot.

3. Componentes Implementados y Funcionalidades
3.1. pizzeria_agents.py (Los "Empleados" del Bot)

CustomerManagementAgent: ✅ Funcional. Identifica, registra y saluda al cliente. Su instruction ha sido pulida para evitar la "alucinación" inicial del print(...).
OrderTakingAgent: ✅ Funcional. Su instruction ahora le obliga a usar herramientas de validación y cálculo.
Valida ítems: Usa get_item_details_by_name para verificar si un producto existe.
Maneja ambigüedad: Si pides "pizza de carne", te presenta las opciones disponibles.
Calcula el total: Usa calculate_order_total al finalizar el pedido.
OrderConfirmationAgent: ✅ Funcional. Muestra el resumen y el total, y pide una confirmación explícita antes de pasar a la recolección de la dirección.
AddressCollectionAgent: ✅ Funcional. Pide la dirección y llama a la herramienta para guardarla tanto en la base de datos como en la memoria de la sesión.
RootOrchestratorAgent: ✅ Funcional. Es el "gerente" que enruta perfectamente a los especialistas según la fase (A, B, C, D, E) y ejecuta el registro final.
3.2. pizzeria_tools.py (Las "Habilidades" del Bot)

Conexión a Base de Datos (Google Sheets):
get_customer_data: Lee la hoja "Clientes" para buscar usuarios existentes.
register_update_customer: Escribe y actualiza filas en la hoja "Clientes". También guarda el nombre y la dirección en la memoria de la sesión para el registro final.
registrar_pedido_finalizado: Escribe una nueva fila en la hoja "Pedidos_Registrados" con todos los detalles del pedido (nombre, ítems, dirección, total), curando la "amnesia".
Lógica de Negocio:
manage_order_item: Añade ítems al "carrito de compras" en la memoria de la sesión de forma robusta.
view_current_order: Permite a los agentes ver el contenido del carrito.
calculate_order_total: Calcula el precio total del pedido basado en precios de ejemplo.
get_item_details_by_name: Valida productos contra el menú, manejando errores y ambigüedades.
get_items_by_category: Permite al bot listar productos de una categoría (ej. "pizzas").
Control de Flujo:
update_session_flow_state: La herramienta clave que permite a los agentes cambiar de fase y hacer que el flujo avance.
4. Próximos Pasos Recomendados
El núcleo del bot está completo y es robusto. La siguiente etapa se centra en expandir su funcionalidad y prepararlo para el mundo real.

Completar la "Base de Datos" (Google Sheets):

Poblar la hoja "Menú" con todos tus productos, categorías y precios reales. Esto hará que calculate_order_total y get_item_details_by_name funcionen con datos de producción.
Implementar el Flujo de Aprobación del Personal:

Notificación: Modificar registrar_pedido_finalizado para que, además de escribir en Sheets, envíe una notificación (vía un bot de Telegram para el personal, por ejemplo) con los detalles del nuevo pedido.
Respuesta del Personal: Crear un mecanismo para que el personal pueda responder a esa notificación para aprobar/rechazar el pedido y añadir el costo de envío.
Notificación al Cliente: Crear un nuevo agente/lógica que se active con la respuesta del personal, actualice el pedido en Sheets con el estado final y el costo de envío, y notifique al cliente.
Despliegue a Producción en Telegram:

Conectar el root_agent que hemos creado a tu archivo telegram_pizzeria_bot.py.
Realizar pruebas exhaustivas directamente en Telegram.
Considerar el despliegue en un servicio en la nube como Cloud Run para que el bot esté disponible 24/7.
Refinamiento Continuo:

Seguir puliendo las instructions de los agentes para hacer a "Angelo" aún más natural y carismático.

Estado del Proyecto: PizzeríaBot v1.0 (Estable y Funcional)
Fecha: 17 de Junio, 2025

1. Resumen Ejecutivo y Visión General
El proyecto PizzeríaBot ha alcanzado un hito fundamental: la culminación de su fase de desarrollo y depuración del núcleo. Hemos transformado con éxito un prototipo inicial en un sistema multi-agente robusto, estable y funcional, utilizando el Agent Development Kit (ADK) de Google.

La arquitectura final se basa en un orquestador central determinista (RootOrchestratorAgent de tipo CustomAgent) que gestiona un equipo de agentes especialistas. Este enfoque, combinado con una estrategia de caché en memoria para el menú (menu.json), ha resuelto los problemas de estabilidad y rendimiento, resultando en un bot rápido y predecible.

El bot ahora es capaz de gestionar una conversación completa y compleja, desde el saludo y registro del cliente, pasando por la toma de un pedido con modificaciones, hasta la confirmación de la dirección y el registro final del pedido en Google Sheets, sin errores críticos que detengan la aplicación.

2. Hitos Alcanzados y Mejoras Implementadas
Gracias a nuestro proceso de depuración iterativo, hemos solucionado problemas complejos y mejorado significativamente el bot:

Estabilidad Total (Cero "Crashes"): Se ha eliminado por completo el AttributeError que detenía la aplicación al finalizar un pedido. La herramienta calculate_order_total ahora es "a prueba de balas" y maneja de forma segura cualquier dato en el carrito, garantizando que el bot siempre pueda completar el flujo.

Rendimiento Excepcional (Caché de Menú): Se ha implementado con éxito la arquitectura de caché en memoria. El bot carga el menu.json una sola vez al iniciar. Esto ha eliminado el 100% de las llamadas repetitivas a Google Sheets para consultas de productos, haciendo que la búsqueda y presentación de ítems del menú sea instantánea.

Lógica de Modificación de Pedidos: Se ha implementado y verificado con éxito el flujo de modificación de pedidos. El OrderConfirmationAgent ahora entiende cuando un usuario quiere hacer un cambio y delega correctamente el control de vuelta al OrderTakingAgent, quien tiene las herramientas para añadir o quitar ítems del carrito. Este es uno de los flujos de usuario más complejos y realistas, y ahora funciona a la perfección.

Manejo de Pedidos Complejos: Se ha solucionado la "amnesia de pedidos múltiples". La nueva instruction del OrderTakingAgent le obliga a procesar un ítem a la vez, guiando al usuario de forma clara y evitando que se pierda información cuando se piden varios productos en una sola frase.

Búsqueda de Productos Mejorada: Se ha refinado la herramienta get_item_details_by_name para ser más precisa y, al mismo tiempo, tolerante a errores de tipeo comunes, mejorando la experiencia de búsqueda.

3. Lo que Falta (Refinamientos Finales para la v1.0)
Aunque el núcleo es estable, quedan dos pequeños bugs de lógica y datos por pulir para considerar la v1.0 completa:

La "Amnesia" Final de la Dirección: Como vimos en el log12, el mensaje de registro final aún muestra la dirección como "No especificada".

Causa: La herramienta registrar_pedido_finalizado no está leyendo la dirección desde la memoria de la sesión (state), que es donde se guarda instantáneamente.
Solución Pendiente: Implementar la versión final de registrar_pedido_finalizado que obtiene la dirección desde state.get('_last_confirmed_delivery_address_for_order').
Búsqueda Inteligente con Sinónimos: El bot todavía no entiende términos como "pepsi de medio litro".

Causa: Nuestro menu.json aún no contiene sinónimos o alias.
Solución Pendiente:
a) Enriquecer el menu.json añadiendo una clave "Alias" a los productos ("Alias": "pepsi medio litro, pepsi personal").
b) Asegurarse de que la herramienta get_item_details_by_name en pizzeria_tools.py utilice la versión que busca tanto en Nombre_Plato como en el campo Alias.
4. Hoja de Ruta (Roadmap) - Próximas Funcionalidades
Con un núcleo estable, podemos planificar con confianza las siguientes grandes funcionalidades:

Implementar la "Ventana de 5 Minutos" para Modificar Pedidos:

Objetivo: Permitir a un usuario añadir ítems a un pedido que acaba de finalizar.
Plan: Activar la herramienta check_if_order_is_modifiable (que ya diseñamos) y las instrucciones inteligentes en el CustomerManagementAgent para que ofrezca esta opción al detectar un pedido reciente.
Implementar el Patrón Transaccional (2 Llamadas a BD):

Objetivo: Alcanzar la máxima eficiencia reduciendo las escrituras a la base de datos a una única operación de "commit" al final.
Plan: Refactorizar los agentes CustomerManagementAgent y AddressCollectionAgent para que solo guarden datos en la memoria de sesión, e implementar la herramienta maestra commit_final_order_and_customer_data que se llamará en la fase final de la orquestación.
Implementar Búsqueda por Ingredientes:

Objetivo: Eliminar por completo la "alucinación" de la IA sobre los ingredientes.
Plan: Añadir una clave "Ingredientes" a cada producto en menu.json y actualizar la instruction del OrderTakingAgent para que use la herramienta get_item_details_by_name y lea este campo para responder preguntas sobre los ingredientes.
Flujo de Aprobación del Personal:

Objetivo: Conectar el bot con el personal de la pizzería para una operación real.
Plan: Implementar la notificación a un chat de Telegram/WhatsApp del personal, un mecanismo para que respondan con la aprobación y el costo de envío, y la lógica para notificar al cliente el estado final.
Capacidades Multimodales (Voz):

Objetivo: Permitir que los clientes hagan pedidos por mensajes de voz.
Plan: Integrar un servicio de Speech-to-Text (como la API de Google) como un pre-procesador en nuestro telegram_pizzeria_bot.py.
5. Conclusión General
El proyecto PizzeríaBot es un éxito rotundo. Hemos superado todos los obstáculos técnicos y de estabilidad, y hemos construido una base de software sólida, profesional y escalable. La arquitectura actual es un ejemplo excelente de cómo diseñar sistemas de agentes fiables.

Tras realizar los 2 refinamientos finales (dirección y alias), podremos dar por finalizada la versión 1.0 del núcleo del bot y pasar con total confianza a la fase de implementación de las nuevas y emocionantes funcionalidades de la hoja de ruta.