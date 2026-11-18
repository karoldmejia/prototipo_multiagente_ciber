"""MCP Server local - Proporciona herramientas accesibles vía MCP protocol.

Versión compatible con mcp SDK 2.3.0 usando la API de bajo nivel (on_* callbacks).
"""

import json
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource,
    Tool,
    TextResourceContents,
    CallToolRequest,
    ErrorData,
    ListToolsResult,
    ListToolsRequest,
    ReadResourceRequest,
    ReadResourceResult,
    ListResourcesRequest,
    ListResourcesResult,
)


def create_server():
    """Crea y configura el servidor MCP con las herramientas definidas."""
    
    server = Server(
        name="mcp-security",
        version="0.1.0",
    )
    
    # Recursos disponibles
    @server.list_resources()
    async def handle_list_resources() -> ListResourcesResult:
        return ListResourcesResult(
            resources=[
                Resource(
                    uri="mcp://security/policy",
                    name="Security Policy",
                    description="Políticas completas de seguridad del sistema",
                    mimeType="text/markdown"
                ),
                Resource(
                    uri="mcp://security/logs",
                    name="Security Logs",
                    description="Logs de seguridad de muestra para análisis",
                    mimeType="text/markdown"
                )
            ]
        )
    
    @server.read_resource()
    async def handle_read_resource(req: ReadResourceRequest) -> ReadResourceResult:
        uri = req.params.resource_uri
        if uri == "mcp://security/policy":
            from pathlib import Path
            policy_path = Path("/home/karold/Documentos/universidad/sem_8/ia_1/prototipo_rag/docs/politicas_seguridad.md")
            text = policy_path.read_text(encoding="utf-8")
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=uri,
                        mimeType="text/markdown",
                        text=text
                    )
                ]
            )
        elif uri == "mcp://security/logs":
            from pathlib import Path
            logs_path = Path("/home/karold/Documentos/universidad/sem_8/ia_1/prototipo_rag/docs/logs_seguridad.md")
            text = logs_path.read_text(encoding="utf-8")
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=uri,
                        mimeType="text/markdown",
                        text=text
                    )
                ]
            )
        else:
            raise ErrorData(code=32601, message=f"Unknown resource: {uri}")
    
    # Herramientas disponibles
    @server.list_tools()
    async def handle_list_tools() -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name="read_security_policy",
                    description="Lee las políticas de seguridad desde el documento local. Solo lectura.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "description": "Sección específica a leer (opcional)."
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="run_injection_test",
                    description="Simula una prueba de inyección en un endpoint objetivo. Requiere aprobación humana (SENSIBLE).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Endpoint o objetivo a probar (ej. 'https://example.com/api')"
                            },
                            "test_type": {
                                "type": "string",
                                "description": "Tipo de prueba ('xss', 'sqli', 'prompt_injection', 'enum')."
                            }
                        },
                        "required": ["target"]
                    }
                )
            ]
        )
    
    @server.call_tool()
    async def handle_call_tool(req: CallToolRequest) -> Any:
        """Ejecuta una herramienta por nombre y retorna el resultado."""
        name = req.params.name
        arguments = req.params.arguments or {}
        
        if name == "read_security_policy":
            section = arguments.get("section", "")
            from pathlib import Path
            policy_path = Path("/home/karold/Documentos/universidad/sem_8/ia_1/prototipo_rag/docs/politicas_seguridad.md")
            text = policy_path.read_text(encoding="utf-8")
            
            if section:
                lines = text.split("\n")
                section_text = []
                current_section = None
                for line in lines:
                    if line.startswith("#"):
                        if current_section and section.lower() in current_section.lower():
                            break
                        current_section = line.strip("#").lower().replace(" ", "_")
                        if section.lower() in current_section:
                            section_text = []
                    if section_text is not None:
                        section_text.append(line)
                result = "\n".join(section_text) if section_text else text
            else:
                result = text
            
            # Retornar usando CallToolResult format
            from mcp.types import CallToolResult, TextContent
            return CallToolResult(
                contents=[
                    TextContent(
                        type="text",
                        text=result
                    )
                ]
            )
        
        elif name == "run_injection_test":
            target = arguments.get("target", "")
            test_type = arguments.get("test_type", "prompt_injection")
            
            # Simulación de prueba de inyección (SENSIBLE - requiere aprobación)
            findings = []
            if test_type == "prompt_injection":
                findings = [
                    {
                        "type": "prompt_injection_detected",
                        "description": "Posible inyección de prompt en parámetros del endpoint",
                        "evidence": "Parametros que contienen 'ignore previous instructions' detectados",
                        "severity": "high"
                    }
                ]
                risk_level = "high"
            elif test_type == "xss":
                findings = [
                    {
                        "type": "xss_potential",
                        "description": "Posible vulnerabilidad XSS detectada",
                        "evidence": "Input no validado reflejo en respuesta",
                        "severity": "medium"
                    }
                ]
                risk_level = "medium"
            elif test_type == "sqli":
                findings = [
                    {
                        "type": "sqli_attempt",
                        "description": "Intento de inyección SQL detectado",
                        "evidence": "Caracteres especiales en input de parámetros",
                        "severity": "high"
                    }
                ]
                risk_level = "high"
            else:
                findings = []
                risk_level = "low"
            
            # Determinar si requiere aprobación
            approval_required = test_type in ["prompt_injection", "sqli"]
            
            result = {
                "target": target,
                "test_type": test_type,
                "simulated": True,
                "findings": findings,
                "risk_level": risk_level,
                "approval_required": approval_required
            }
            
            from mcp.types import CallToolResult, TextContent
            return CallToolResult(
                contents=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            )
        
        else:
            from mcp.types import CallToolResult, TextContent, ErrorData
            return CallToolResult(
                contents=[
                    TextContent(
                        type="text",
                        text=f"Herramienta desconocida: {name}"
                    )
                ],
                isError=True,
                error=ErrorData(code=32601, message=f"Unknown tool: {name}")
            )
    
    return server


def read_security_policy_tool(section: str = "") -> dict:
    """Ejecuta read_security_policy y retorna un diccionario con el resultado.
    
    Esta función helper permite al orquestador invocar la herramienta MCP
    sin necesidad del flujo stdio completo, ideal para prototipado y tests.
    """
    from pathlib import Path
    policy_path = Path("/home/karold/Documentos/universidad/sem_8/ia_1/prototipo_rag/docs/politicas_seguridad.md")
    text = policy_path.read_text(encoding="utf-8")
    
    if section:
        lines = text.split("\n")
        section_text = []
        current_section = None
        for line in lines:
            if line.startswith("#"):
                if current_section and section.lower() in current_section.lower():
                    break
                current_section = line.strip("#").lower().replace(" ", "_")
                if section.lower() in current_section:
                    section_text = []
            if section_text is not None:
                section_text.append(line)
        result = "\n".join(section_text) if section_text else text
    else:
        result = text
    
    return {
        "content": [
            {
                "type": "text",
                "text": result
            }
        ],
        "isError": False
    }

def run_injection_test_tool(target: str, test_type: str = "prompt_injection") -> dict:
    """Ejecuta run_injection_test y retorna un diccionario con el resultado."""
    findings = []
    if test_type == "prompt_injection":
        findings = [
            {
                "type": "prompt_injection_detected",
                "description": "Posible inyección de prompt en parámetros del endpoint",
                "evidence": "Parametros que contienen 'ignore previous instructions' detectados",
                "severity": "high"
            }
        ]
        risk_level = "high"
    elif test_type == "xss":
        findings = [
            {
                "type": "xss_potential",
                "description": "Posible vulnerabilidad XSS detectada",
                "evidence": "Input no validado reflejo en respuesta",
                "severity": "medium"
            }
        ]
        risk_level = "medium"
    elif test_type == "sqli":
        findings = [
            {
                "type": "sqli_attempt",
                "description": "Intento de inyección SQL detectado",
                "evidence": "Caracteres especiales en input de parámetros",
                "severity": "high"
            }
        ]
        risk_level = "high"
    else:
        findings = []
        risk_level = "low"
    
    approval_required = test_type in ["prompt_injection", "sqli"]
    
    result = {
        "target": target,
        "test_type": test_type,
        "simulated": True,
        "findings": findings,
        "risk_level": risk_level,
        "approval_required": approval_required
    }
    
    from mcp.types import CallToolResult, TextContent
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2, ensure_ascii=False)
            }
        ],
        "isError": False
    }

def main():
    """Punto de entrada para ejecutar el servidor MCP."""
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def run():
        server = create_server()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-security",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(),
                ),
            )
    
    asyncio.run(run())


if __name__ == "__main__":
    main()