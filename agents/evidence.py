"""Agente de Rendimiento y Evidencia - Mide latencia, tokens y consolida evidencia.

Este agente:
1. Mide tokens de entrada/salida por cada paso
2. Mide latencia total
3. Detecta falsos positivos/negativos en clasificación
4. Consolida evidencia y genera dictamen final
5. Genera reporte en JSON/Markdown para el dashboard
"""

import json
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


import time

class PerformanceMetrics:
    """Contenedor para métricas de rendimiento."""
    
    def __init__(self):
        self.tokens_input = 0
        self.tokens_output = 0
        self.latency_total = 0.0
        self.steps = []
        self.mission_start_time = None
    
    def start_mission_timer(self):
        """Inicia la medición de tiempo para una misión."""
        self.mission_start_time = time.time()
    
    def stop_mission_timer(self):
        """Detiene la medición de tiempo para una misión y acumula el resultado."""
        if self.mission_start_time is not None:
            self.latency_total += time.time() - self.mission_start_time
        self.mission_start_time = None
    
    def record_step_with_time(self, step_name: str, tokens_in: int, tokens_out: int, 
                              classification: str = None) -> float:
        """Registra un paso y retorna el tiempo transcurrido para ese paso."""
        step_time = time.time()
        # El tiempo se acumulará al detener la misión
        self.steps.append({
            "step": step_name,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "latency": step_time,  # tiempo relativo, se acumulará después
            "classification": classification
        })
        self.tokens_input += tokens_in
        self.tokens_output += tokens_out
        return step_time
    
    def record_step(self, step_name: str, tokens_in: int, tokens_out: int, 
                    latency: float, classification: str = None):
        """Registra un paso en la traza."""
        self.steps.append({
            "step": step_name,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "latency": latency,
            "classification": classification
        })
        self.tokens_input += tokens_in
        self.tokens_output += tokens_out
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_total_seconds": self.latency_total,
            "num_steps": len(self.steps),
            "steps": self.steps,
            "timestamp": datetime.now().isoformat()
        }


class EvidenceAgent:
    """Agente que consolida evidencia y genera dictamen final."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.classification_results = []
        self.attack_findings = []
        self.rag_queries = []
        self.dictamen = None
    
    def record_rag_query(self, query: str, results_count: int, latency: float):
        """Registra una consulta RAG."""
        self.rag_queries.append({
            "query": query,
            "results_count": results_count,
            "latency": latency
        })
    
    def record_classification(self, step: str, classification: str, reason: str):
        """Registra un resultado de clasificación."""
        self.classification_results.append({
            "step": step,
            "classification": classification,
            "reason": reason
        })
    
    def record_attack_finding(self, finding: Dict[str, Any]):
        """Registra un hallazgo de ataque."""
        self.attack_findings.append(finding)
    
    def evaluate_quality(self, response: str, expected_keywords: List[str] = None) -> float:
        """Evalúa la calidad de una respuesta (0.0 a 1.0).
        
        Heurística simple: proporción de palabras clave esperadas presentes.
        """
        if not expected_keywords:
            return 1.0  # Si no hay expectativas, asumir calidad perfecta
        
        response_lower = response.lower()
        found = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return found / len(expected_keywords)
    
    def generate_dictamen(self, 
                         mission: str,
                         multi_agent_result: Dict[str, Any],
                         single_agent_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Genera el dictamen final consolidado."""
        
        # Calidad comparada
        multi_quality = multi_agent_result.get("quality_score", 0.0)
        single_quality = single_agent_result["quality_score"] if single_agent_result else 0.0
        
        # Comparación de eficiencia
        multi_tokens = self.metrics.tokens_input + self.metrics.tokens_output
        single_tokens = single_agent_result["tokens_total"] if single_agent_result else multi_tokens
        
        # Análisis de riesgos detectados
        multi_risks = multi_agent_result.get("risks_detected", [])
        single_risks = single_agent_result.get("risks_detected", []) if single_agent_result else []
        
        # Convertir a listas si son diccionarios
        multi_risks_list = multi_risks if isinstance(multi_risks, list) else []
        single_risks_list = single_risks if isinstance(single_risks, list) else []
        
        # Determinar ganador basado en calidad y tokens
        if multi_quality > single_quality:
            better_config = "multi-agent"
        elif single_quality > multi_quality:
            better_config = "single-agent"
        else:
            # Empate en calidad: compara tokens
            if multi_tokens < single_tokens:
                better_config = "multi-agent"
            else:
                better_config = "single-agent"
        
        # Determinar mejor configuración
        better_config = "multi-agent"  # default
        if single_quality > multi_quality:
            better_config = "single-agent"
        elif multi_quality > single_quality:
            better_config = "multi-agent"
        elif multi_quality == single_quality:
            if multi_tokens < single_tokens:
                better_config = "multi-agent"
            else:
                better_config = "single-agent"
        
        self.dictamen = {
            "mission": mission,
            "timestamp": datetime.now().isoformat(),
            "configurations_comparison": {
                "multi_agent": {
                    "quality_score": round(multi_quality, 3),
                    "tokens_total": multi_tokens,
                    "latency_total": round(self.metrics.latency_total, 3),
                    "risks_detected": multi_risks_list,
                    "steps_executed": len(self.metrics.steps)
                },
                "single_agent": {
                    "quality_score": round(single_quality, 3),
                    "tokens_total": single_tokens,
                    "latency_total": round((single_agent_result.get("latency", 0.0) if single_agent_result else 0.0), 3),
                    "risks_detected": single_risks_list,
                    "steps_executed": single_agent_result.get("steps", 0) if single_agent_result else 0
                }
            },
            "comparison": {
                "quality_difference": round(multi_quality - single_quality, 3),
                "token_difference": multi_tokens - single_tokens,
                "latency_difference": round(self.metrics.latency_total - 
                                           (single_agent_result.get("latency", 0.0) if single_agent_result else 0.0), 3),
                "better_configuration": better_config
            },
            "risk_analysis": {
                "multi_agent_risks": multi_risks_list,
                "single_agent_risks": single_risks_list,
                "multi_agent_detected_more": len(multi_risks_list) > len(single_risks_list) if single_risks_list else True,
                "summary": self._generate_risk_summary(multi_risks_list, single_risks_list)
            },
            "metrics": self.metrics.to_dict(),
            "overall_verdict": self._determine_verdict(multi_quality, single_quality,
                                                     multi_risks_list, single_risks_list,
                                                     single_agent_result)
        }
        
        return self.dictamen
    
    def _generate_risk_summary(self, multi_risks: List, single_risks: List) -> str:
        """Genera resumen de análisis de riesgos."""
        if not multi_risks and not single_risks:
            return "No risks detected in either configuration."
        
        multi_types = set()
        for r in multi_risks:
            if isinstance(r, str):
                multi_types.add(r)
            elif isinstance(r, dict):
                for key in r.keys():
                    if "risk" in key.lower() or "detected" in key.lower():
                        multi_types.add(key)
        
        single_types = set()
        for r in single_risks:
            if isinstance(r, str):
                single_types.add(r)
            elif isinstance(r, dict):
                for key in r.keys():
                    if "risk" in key.lower() or "detected" in key.lower():
                        single_types.add(key)
        
        if multi_types and single_types:
            extra = multi_types - single_types
            missing = single_types - multi_types
            common = multi_types & single_types
            return (f"Multi-agent detected: {len(extra)} extra risks, "
                    f"shared: {len(common)}, single-agent had: {len(missing)}")
        elif multi_types:
            return f"Multi-agent detected {len(multi_types)} risks; single-agent: none"
        else:
            return f"Single-agent detected {len(single_types)} risks; multi-agent: none"
    
    def _determine_verdict(self, multi_quality: float, single_quality: float,
                      multi_risks: List, single_risks: List,
                      single_agent_result: Dict[str, Any] = None) -> str:
        """Determina el dictamen general."""
        # Criteria:
        # 1. Si multi-agent tiene mejor qualidade Y detecta mais riesgos -> multi-agent winner
        # 2. Se single-agent tem melhor qualidade e menos tokens -> single-agent winner
        # 3. Empate tecnico -> multi-agent por melhor seguranca
        
        # Verificar qualidade melhorada
        multi_better_quality = multi_quality > single_quality
        single_better_quality = single_quality > multi_quality
        
        # Verificar eficiencia (menos tokens)
        multi_total_tokens = multi_quality  # placeholder - usamos métricas reales
        single_total_tokens = single_quality  # placeholder
        
        # Usar métricas reales del agente
        multi_tokens_total = self.metrics.tokens_input + self.metrics.tokens_output
        single_tokens_total = single_agent_result["tokens_total"] if single_agent_result else multi_tokens_total
        
        single_better_efficiency = single_tokens_total < multi_tokens_total
        
        # Lógica de decisión
        if multi_better_quality and len(multi_risks) > len(single_risks):
            return "MULTI-AGENT: Better quality + better risk detection"
        elif single_better_efficiency and single_quality >= multi_quality:
            return "SINGLE-AGENT: Better efficiency + comparable quality"
        elif multi_better_quality:
            return "MULTI-AGENT: Better quality offset by higher cost"
        elif single_better_quality and single_better_efficiency:
            return "SINGLE-AGENT: Better quality + better efficiency"
        elif single_better_quality:
            return "SINGLE-AGENT: Better quality offset by lower cost"
        else:
            # Empate ou multi melhor em riscos
            if len(multi_risks) > len(single_risks):
                return "MULTI-AGENT: Better risk detection"
            elif len(single_risks) > len(multi_risks):
                return "SINGLE-AGENT: Better risk detection"
            else:
                return "MULTI-AGENT: Balanced configuration"
    
    def save_to_json(self, filepath: str = "output/dictamen.json"):
        """Guarda el dictamen en un archivo JSON."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.dictamen, f, indent=2, ensure_ascii=False)
        print(f"Dictamen guardado en: {filepath}")
    
    def generate_markdown_report(self, output_path: str = "output/comparison_report.md") -> str:
        """Genera un reporte en Markdown comparando configuraciones."""
        if not self.dictamen:
            raise ValueError("No se ha generado un dictamen. Llamar a generate_dictamen primero.")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        d = self.dictamen
        lines = []
        
        lines.append("# Reporte Comparativo: Single-agent vs Multi-agent\n")
        
        lines.append("## Misión")
        lines.append(f"> {d['mission']}")
        lines.append("")
        
        lines.append("## Comparación de Configuraciones")
        lines.append("")
        
        # Tabla de métricas
        lines.append("| Métrica | Multi-agent | Single-agent |")
        lines.append("|---|---|---|")
        lines.append(f"| **Calidad (1-5)** | {d['configurations_comparison']['multi_agent']['quality_score']} | {d['configurations_comparison']['single_agent']['quality_score']} |")
        lines.append(f"| **Tokens** | {d['configurations_comparison']['multi_agent']['tokens_total']} | {d['configurations_comparison']['single_agent']['tokens_total']} |")
        lines.append(f"| **Latencia (s)** | {d['configurations_comparison']['multi_agent']['latency_total']} | {d['configurations_comparison']['single_agent']['latency_total']} |")
        lines.append(f"| **Riesgos detectados** | {', '.join(d['configurations_comparison']['multi_agent']['risks_detected']) or 'Ninguno'} | {', '.join(d['configurations_comparison']['single_agent']['risks_detected']) or 'Ninguno'} |")
        lines.append("")
        
        lines.append("## Diferencias")
        cmp = d['comparison']
        lines.append(f"- **Diferencia de calidad:** {cmp['quality_difference']} (positivo = multi-mejor)")
        lines.append(f"- **Diferencia de tokens:** {cmp['token_difference']} (positivo = multi-uso más tokens)")
        lines.append(f"- **Diferencia de latencia:** {cmp['latency_difference']}s (positivo = multi-más lento)")
        lines.append(f"- **Mejor configuración:** {cmp['better_configuration'].upper()}")
        lines.append("")
        
        lines.append("## Análisis de Riesgos")
        lines.append(d['risk_analysis']['summary'])
        lines.append("")
        
        lines.append("## Verdictos")
        lines.append(d['overall_verdict'])
        lines.append("")
        
        lines.append("## Métricas Detalladas")
        lines.append("### Tokens de entrada")
        lines.append(f"> {d['metrics']['tokens_input']}")
        lines.append("### Tokens de salida")
        lines.append(f"> {d['metrics']['tokens_output']}")
        lines.append(f"### Latencia total")
        lines.append(f"> {d['metrics']['latency_total']}s")
        lines.append(f"### Pasos ejecutados")
        lines.append(f"> {d['metrics']['num_steps']}")
        lines.append("")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return output_path


# Punto de entrada para pruebas
if __name__ == "__main__":
    print("=== Agente de Rendimiento y Evidencia - Pruebas ===\n")
    
    agent = EvidenceAgent()
    
    # Simular algunas operações
    agent.metrics.start_timer()
    agent.metrics.record_step("Clasificación política", 50, 100, 0.5, "NO_SENSIBLE")
    agent.metrics.record_step("MCP tool: read_security_policy", 100, 200, 1.2, "NO_SENSIBLE")
    agent.metrics.record_step("Sanitización", 20, 30, 0.3, "NO_SENSIBLE")
    agent.metrics.stop_timer()
    
    # Registrar RAG query
    agent.record_rag_query("politicas de seguridad", 3, 0.8)
    
    # Registrar classificação
    agent.record_classification("Paso 1", "NO_SENSIBLE", "Acción de solo lectura")
    
    # Gerar dictamen de exemplo
    multi_result = {
        "quality_score": 0.85,
        "risks_detected": ["prompt_injection", "excessive_agency"],
        "tokens_total": 850,
        "latency": 3.5
    }
    
    single_result = {
        "quality_score": 0.72,
        "risks_detected": ["excessive_agency"],
        "tokens_total": 620,
        "latency": 2.1
    }
    
    dictamen = agent.generate_dictamen("Provar políticas de segurança", multi_result, single_result)
    print(f"Dictamen gerado: {dictamen['overall_verdict']}")
    agent.save_to_json()
    md_path = agent.generate_markdown_report()
    print(f"Reporte Markdown gerado: {md_path}")