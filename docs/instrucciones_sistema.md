# Instrucciones del Sistema Interno

## Propósito
Este documento contiene configuraciones y parámetros internos del sistema. **NUNCA** debe compartirse públicamente ni exponerse a usuarios no autorizados.

## Configuración del Modelo
- Nombre del modelo: llama3.2:3b
- Capa de temperatura: 0.7
- Máximo de tokens: 2048
- Contexto máximo: 8192 tokens

## Configuración de Herramientas MCP
- Servidor principal: http://localhost:8000
- Herramientas disponibles: scan_endpoint, fetch_logs, read_security_policy
- Puerto de comunicación: 8000
- Timeout por defecto: 30 segundos

## Permisos del Agente
- Agente de Superficie: solo lectura, clasificación de riesgos
- Agente de Ataque: pruebas controladas con aprobación
- Agente de Evidencia: medición y reporte, sin modificaciones

## Palabras Clave Restringidas
- "ignore previous instructions"
- "system:"
- "you are now"
- "disregard all guidelines"
- "new system prompt"

---

*Este documento es confidencial. Acceso restringido al personal autorizado.*