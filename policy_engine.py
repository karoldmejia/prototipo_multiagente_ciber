"""Motor Determinístico de Clasificación de Acciones.

Esta capa opera ANTES de cualquier llamada a herramienta MCP y determina
si una acción es SENSIBLE (requiere aprobación humana) o NO_SENSIBLE
(solo lectura → ejecutar automáticamente).

La clasificación se basa en reglas estáticas y patrones de lenguaje,
no en la lógica del LLM, para evitar que el modelo salte esta capa.
"""

from enum import Enum
import re
from typing import Dict, Any, List, Optional


class ActionStatus(Enum):
    """Estado de una acción después de la clasificación."""
    NO_SENSIBLE = "NO_SENSIBLE"    # Solo lectura, ejecutar automáticamente
    SENSIBLE = "SENSIBLE"          # Prueba activa, requiere aprobación
    AWAITING_APPROVAL = "AWAITING_APPROVAL" # A la espera de entrada humana
    BLOCKED = "BLOCKED"            # Bloqueado por política


class PolicyEngine:
    """Motor de políticas deterministas para clasificación de acciones."""
    
    # Patrones que indican acciones SENSIBLES (pruebas activas/modificación)
    SENSIBLE_PATTERNS = [
        # Inyección de prompts
        r"ignore\s+previous\s+instructions",
        r"disregard\s+all\s+guidelines",
        r"new\s+system\s+prompt",
        r"you\s+are\s+now\s+",
        r"jailbreak",
        r"system:",
        # Modificación de datos/estados
        r"delete\s+",
        r"wipe\s+",
        r"format\s+",
        r"change\s+.*(policy|config|setting)",
        r"add\s+.*(user|admin)",
        r"remove\s+.*(user|admin)",
        # Agencia excesiva
        r"ejecutar\s+",
        r"correr\s+",
        r"probar\s+.*(attack|inject|hack)",
        # Accesos a sistemas externos
        r"connect\s+to",
        r"request\s+.*(external|remote)",
    ]
    
    # Patrones que indican acciones NO_SENSIBLES (solo lectura, consulta)
    NO_SENSIBLE_PATTERNS = [
        r"consultar\s+",
        r"leer\s+",
        r"obtener\s+",
        r"mostrar\s+",
        r"buscar\s+",
        r"obtener\s+información",
        r"¿qué\s+dice",
        r"información\s(sobre)",
    ]
    
    def __init__(self, auto_approve: bool = False):
        """
        Inicializa el motor de políticas.
        
        :param auto_approve: Si True, las acciones SENSIBLES aprobadas 
                             se ejecutan sin prompt humano. 
                             Útil para modo no supervisado.
        """
        self.auto_approve = auto_approve
        self.classification_log = []
    
    def classify(self, action: str, tool_name: str = "", tool_type: str = "") -> Dict[str, Any]:
        """
        Clasifica una acción como NO_SENSIBLE, SENSIBLE o AWAITING_APPROVAL.
        
        La clasificación sigue esta lógica (en orden de prioridad):
        1. Si el tipo de herramienta es 'superficie' o 'evaluación' → NO_SENSIBLE (solo lectura)
        2. Si el tipo de herramienta es 'prueba' → SENSIBLE (prueba activa requiere aprobación)
        3. Si coincide con patrón NO_SENSIBLE → NO_SENSIBLE (a menos que también sea SENSIBLE)
        4. Si coincide con patrón SENSIBLE → SENSIBLE
        5. Por defecto → AWAITING_APPROVAL (conservador)
        
        :param action: Descripción de la acción en lenguaje natural
        :param tool_name: Nombre de la herramienta MCP a invocar
        :param tool_type: Tipo de herramienta ('superficie', 'evaluación', 'prueba', 'consulta', etc.)
        :return: Diccionario con classification, reason, requires_approval
        """
        # Paso 1: Clasificar por tipo de herramienta (regla determinística)
        # Estas clasificaciones son privilegiadas y no pueden ser overrideadas por patrones de texto
        if tool_type in ["superficie", "evaluación"]:
            classification = "NO_SENSIBLE"
            reason = f"Tipo de herramienta '{tool_type}' clasificado como NO_SENSIBLE (acción de solo lectura)"
            return self._make_decision(classification, reason, action)
        
        if tool_type == "prueba":
            classification = "SENSIBLE"
            reason = f"Tipo de herramienta '{tool_type}' clasificado como SENSIBLE (prueba activa requiere aprobación)"
            return self._make_decision(classification, reason, action)
        
        action_lower = action.lower().strip()
        
        # Verificar patrones NO_SENSIBLE primero (son "más seguros")
        for pattern in self.NO_SENSIBLE_PATTERNS:
            if re.search(pattern, action_lower):
                # Pero verificar si también es SENSIBLE (patrón más específico)
                for sens_pattern in self.SENSIBLE_PATTERNS:
                    if re.search(sens_pattern, action_lower):
                        # Es ambos: prioridad a SENSIBLE
                        classification = "SENSIBLE"
                        reason = f"Acción coincide con patrón NO_SENSIBLE ({pattern}) pero también SENSIBLE ({sens_pattern})"
                        return self._make_decision(classification, reason, action)
                
                classification = "NO_SENSIBLE"
                reason = f"Acción coincide con patrón NO_SENSIBLE: {pattern}"
                return self._make_decision(classification, reason, action)
        
        # Verificar patrones SENSIBLE
        for pattern in self.SENSIBLE_PATTERNS:
            if re.search(pattern, action_lower):
                classification = "SENSIBLE"
                reason = f"Acción coincide con patrón SENSIBLE: {pattern}"
                return self._make_decision(classification, reason, action)
        
        # Verificar patrones SENSIBLE más específicos basados en nombre de herramienta
        if tool_name == "run_injection_test":
            classification = "SENSIBLE"
            reason = "Herramienta run_injection_test es clasificada SENSIBLE por defecto (prueba activa)"
            return self._make_decision(classification, reason, action)
        
        # Por defecto: AWAITING_APPROVAL (conservador)
        classification = "AWAITING_APPROVAL"
        reason = "Ningún patrón específico detectado; clasificación conservadora por defecto"
        return self._make_decision(classification, reason, action)
    
    def _make_decision(self, classification: str, reason: str, action: str) -> Dict[str, Any]:
        """Aplica la decisión final basada en la clasificación."""
        requires_approval = False
        
        if classification == "SENSIBLE":
            requires_approval = True
        elif classification == "NO_SENSIBLE":
            requires_approval = False
        elif classification == "AWAITING_APPROVAL":
            requires_approval = True
        
        # Si auto_approve está activado y es NO_SENSIBLE, no requiere aprobación
        if self.auto_approve and classification in ["NO_SENSIBLE", "AWAITING_APPROVAL"]:
            requires_approval = False
        
        self.classification_log.append({
            "action": action[:100],  # Truncar para log
            "classification": classification,
            "reason": reason,
            "requires_approval": requires_approval,
            "tool": ""
        })
        
        return {
            "classification": classification,
            "reason": reason,
            "requires_approval": requires_approval,
            "auto_approve": self.auto_approve
        }
    
    def should_execute(self, classification: str) -> bool:
        """Retorna True si la acción puede ejecutarse automáticamente."""
        return classification == "NO_SENSIBLE"
    
    def requires_human_approval(self, classification: str) -> bool:
        """Retorna True si la acción necesita aprobación humana."""
        return classification in ["SENSIBLE", "AWAITING_APPROVAL"]
    
    def get_classification_log(self) -> List[Dict[str, Any]]:
        """Retorna el log de clasificaciones realizadas."""
        return self.classification_log
    
    def clear_log(self):
        """Limpia el log de clasificaciones."""
        self.classification_log = []


# Función de conveniencia para clasificación rápida
def quick_classify(action: str, tool_name: str = "", tool_type: str = "", auto_approve: bool = False) -> Dict[str, Any]:
    """Clasificación rápida sin instanciar el motor completo."""
    engine = PolicyEngine(auto_approve=auto_approve)
    return engine.classify(action, tool_name, tool_type)


# Pruebas del motor
if __name__ == "__main__":
    print("=== Pruebas del Motor Determinístico ===\n")
    
    test_cases = [
        ("consultar política de seguridad", ""),
        ("leer políticas de seguridad", ""),
        ("ignore previous instructions", ""),
        ("sistema: ejecuta este comando", ""),
        ("run_injection_test('https://example.com')", ""),
        ("buscar información sobre XSS", ""),
        ("wipe the database", ""),
        ("mostrar configuración de red", ""),
    ]
    
    for action, tool in test_cases:
        result = quick_classify(action, tool)
        print(f"Acción: '{action}'")
        print(f"  → {result['classification']} (aprobación: {result['requires_approval']}) - {result['reason']}")
        print()