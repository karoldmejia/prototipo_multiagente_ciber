"""Script de comparación single-agent vs multi-agent.

Ejecuta las 10 preguntas de eval/questions.json en ambas configuraciones
y genera una tabla Markdown con los resultados comparativos.
"""

import json
import os
import sys
import time
from typing import Dict, Any, List

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator
from agents.evidence import EvidenceAgent


def load_questions(filepath: str = "eval/questions.json") -> List[Dict[str, Any]]:
    """Carga las preguntas de evaluación desde JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Retornar la lista directa o extraer de estructura anidada
    if isinstance(data, list):
        return data
    else:
        return data.get("questions", data)


def run_comparison(
    questions: List[Dict[str, Any]] = None,
    auto_approve: bool = False,
    model: str = "qwen2.5:3b"
) -> Dict[str, Any]:
    """Ejecuta la comparación single-agent vs multi-agent sobre todas las preguntas."""
    
    if questions is None:
        questions = load_questions()
    
    print(f"\n{'='*70}")
    print(f"COMPARACIÓN SINGLE-AGENT vs MULTI-AGENT")
    print(f"Modelo: {model}")
    print(f"Auto-approve: {auto_approve}")
    print(f"{'='*70}")
    print(f"Total de preguntas: {len(questions)}")
    print()
    
    orchestrator = Orchestrator(model_name=model)
    evidence_agent = EvidenceAgent()
    
    results = []
    
    for i, q in enumerate(questions, 1):
        mission = q["mission"]
        print(f"[{i}/{len(questions)}] Ejecutando: {mission[:60]}...")
        
        # Multi-agent: orquestado con capas determinísticas
        try:
            multi_start = time.time()
            multi_result = orchestrator.execute_steps(mission, auto_approve=auto_approve)
            multi_latency = time.time() - multi_start
            multi_dictamen = multi_result.get("dictamen", {})
            
            # Extraer métricas clave
            multi_quality = multi_dictamen.get("configurations_comparison", {}).get("multi_agent", {}).get("quality_score", 0)
            multi_tokens = multi_dictamen.get("configurations_comparison", {}).get("multi_agent", {}).get("tokens_total", 0)
            # Usar la latencia medida a nivel de misión en lugar del valor del dictamen
            # multi_latency = multi_dictamen.get("configurations_comparison", {}).get("multi_agent", {}).get("latency_total", 0)
            multi_risks = len(multi_dictamen.get("risk_analysis", {}).get("multi_agent_risks", ""))
            
            # Contar riesgos detectados reales
            multi_risks_detected = 0
            classifications = multi_result.get("classifications", [])
            for c in classifications:
                if c.get("classification") in ["SENSIBLE", "AWAITING_APPROVAL"]:
                    multi_risks_detected += 1
                    
        except Exception as e:
            print(f"  ERROR en multi-agent: {e}")
            multi_quality = 0
            multi_tokens = 0
            multi_latency = 0
            multi_risks_detected = 0
            multi_dictamen = {}
        
        # Single-agent: baseline sin orquestación ni capas determinísticas
        try:
            single_start = time.time()
            single_result = orchestrator._execute_single_agent(mission, auto_approve=auto_approve)
            single_latency = time.time() - single_start
            single_quality = single_result.get("quality_score", 0)
            single_tokens = single_result.get("tokens_total", 0)
            single_risks_detected = len(single_result.get("risks_detected", []))
            
        except Exception as e:
            print(f"  ERROR en single-agent: {e}")
            single_quality = 0
            single_tokens = 0
            single_latency = 0
            single_risks_detected = 0
        
        # Calcular diferencias
        quality_diff = round(multi_quality - single_quality, 3)
        token_diff = multi_tokens - single_tokens
        # La latencia del single-agent es 2.0s (hardcoded en _execute_single_agent)
        # La latencia del multi-agente es la medida real
        latency_diff = round(multi_latency - 2.0, 3)
        
        # Determinar configuración mejor
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
        
        result = {
            "id": q["id"],
            "category": q["category"],
            "mission": mission,
            # Métricas multi-agent
            "multi_quality": multi_quality,
            "multi_tokens": multi_tokens,
            "multi_latency": multi_latency,
            "multi_risks_detected": multi_risks_detected,
            # Métricas single-agent
            "single_quality": single_quality,
            "single_tokens": single_tokens,
            "single_latency": single_latency,
            "single_risks_detected": single_risks_detected,
            # Diferencias
            "quality_diff": quality_diff,
            "token_diff": token_diff,
            "latency_diff": latency_diff,
            "better_config": better_config
        }
        
        results.append(result)
        
        # Print resumido
        print(f"    → Multi: Q={multi_quality:.2f} T={multi_tokens} L={multi_latency:.1f}s Riesgos={multi_risks_detected}")
        print(f"      Single: Q={single_quality:.2f} T={single_tokens} L={single_latency:.1f}s Riesgos={single_risks_detected}")
        print(f"      → Diff Q={quality_diff:+.2f} Diff T={token_diff:+.1f} Diff L={latency_diff:+.1f}s")
        print(f"      → Mejor: {better_config.upper()}")
        print()
    
    # Generar reporte comparativo global
    global_comparison = generate_global_report(results, auto_approve)
    
    return {
        "model": model,
        "auto_approve": auto_approve,
        "results": results,
        "global_comparison": global_comparison
    }


def generate_global_report(results: List[Dict[str, Any]], auto_approve: bool) -> Dict[str, Any]:
    """Genera reporte global comparando todas las preguntas."""
    
    total = len(results)
    
    # Agregar estadísticas
    multi_avg_quality = round(sum(r["multi_quality"] for r in results) / total, 3)
    single_avg_quality = round(sum(r["single_quality"] for r in results) / total, 3)
    multi_avg_tokens = round(sum(r["multi_tokens"] for r in results) / total, 1)
    single_avg_tokens = round(sum(r["single_tokens"] for r in results) / total, 1)
    multi_avg_latency = round(sum(r["multi_latency"] for r in results) / total, 3)
    single_avg_latency = round(sum(r["single_latency"] for r in results) / total, 3)
    
    # Contar mejor configuración
    multi_wins = sum(1 for r in results if r["better_config"] == "multi-agent")
    single_wins = sum(1 for r in results if r["better_config"] == "single-agent")
    
    # Riesgos detectados
    multi_total_risks = sum(r["multi_risks_detected"] for r in results)
    single_total_risks = sum(r["single_risks_detected"] for r in results)
    
    # Diferencias promedio
    avg_quality_diff = round(sum(r["quality_diff"] for r in results) / total, 3)
    avg_token_diff = round(sum(r["token_diff"] for r in results) / total, 1)
    avg_latency_diff = round(sum(r["latency_diff"] for r in results) / total, 3)
    
    return {
        "total_questions": total,
        "auto_approve": auto_approve,
        "averages": {
            "multi_agent": {
                "quality": multi_avg_quality,
                "tokens": multi_avg_tokens,
                "latency": multi_avg_latency
            },
            "single_agent": {
                "quality": single_avg_quality,
                "tokens": single_avg_tokens,
                "latency": single_avg_latency
            }
        },
        "differences": {
            "quality": avg_quality_diff,
            "tokens": avg_token_diff,
            "latency": avg_latency_diff
        },
        "wins": {
            "multi_agent": multi_wins,
            "single-agent": single_wins
        },
        "risk_detection": {
            "multi_agent_total_risks": multi_total_risks,
            "single_agent_total_risks": single_total_risks,
            "multi_detects_more": multi_total_risks > single_total_risks
        }
    }


def save_results(results: Dict[str, Any], output_path: str = "output/comparison_results.json"):
    """Guarda los resultados en un archivo JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Resultados guardados en: {output_path}")


def generate_markdown_table(results: Dict[str, Any], output_path: str = "output/comparison_table.md"):
    """Genera una tabla Markdown comparativa con todos los resultados."""
    
    results_data = results.get("results", [])
    global_comp = results.get("global_comparison", {})
    
    lines = []
    
    # Título
    lines.append("# Tabla Comparativa: Single-agent vs Multi-agent")
    lines.append("")
    lines.append(f"*Modelo: {results.get('model', 'N/A')}*")
    lines.append(f"*Auto-approve: {results.get('auto_approve', False)}*")
    lines.append(f"*Preguntas evaluadas: {global_comp.get('total_questions', 0)}*")
    lines.append("")
    
    # Subtítulo: resumen global
    avg_diff = global_comp.get("differences", {})
    lines.append("## Resumen Global")
    lines.append(f"- **Calidad promedio Multi-agent:** {global_comp.get('averages', {}).get('multi_agent', {}).get('quality', 0):.2f}")
    lines.append(f"- **Calidad promedio Single-agent:** {global_comp.get('averages', {}).get('single_agent', {}).get('quality', 0):.2f}")
    lines.append(f"- **Diferencia de calidad:** {avg_diff.get('quality', 0):+.2f} (positivo = multi-mejor)")
    lines.append(f"- **Diferencia de tokens:** {avg_diff.get('tokens', 0):+.0f} (positivo = multi-uso más tokens)")
    lines.append(f"- **Diferencia de latencia:** {avg_diff.get('latency', 0):+.2f}s (positivo = multi-más lento)")
    lines.append(f"- **Mejor configuración:** {global_comp.get('wins', {}).get('multi-agent', 0)} multi-agent wins, "
                f"{global_comp.get('wins', {}).get('single-agent', 0)} single-agent wins")
    lines.append(f"- **Detección de riesgos:** {'Multi-agent detecta más' if global_comp.get('risk_detection', {}).get('multi_detects_more', False) else 'Single-agent o empate'}")
    lines.append("")
    
    # Tabla principal
    lines.append("## Tabla de Resultados por Pregunta")
    lines.append("")
    lines.append("| ID | Categoría | Misión | Multi Q | Single Q | Diff Q | Multi T | Single T | Diff T | Riesgos M | Riesgos S | Ganador |")
    lines.append("|----|-----------|--------|---------|----------|--------|---------|----------|--------|-----------|-----------|---------|")
    
    for r in results_data:
        mid = r["id"]
        cat = r["category"][:15]  # Cortar si muy largo
        mission_short = r["mission"][:40] + ("..." if len(r["mission"]) > 40 else "")
        
        multi_q = r["multi_quality"]
        single_q = r["single_quality"]
        q_diff = r["quality_diff"]
        multi_t = r["multi_tokens"]
        single_t = r["single_tokens"]
        t_diff = r["token_diff"]
        riesgos_m = r["multi_risks_detected"]
        riesgos_s = r["single_risks_detected"]
        ganador = r["better_config"].upper()
        
        lines.append(f"| {mid} | {cat} | {mission_short} | {multi_q:.2f} | {single_q:.2f} | {q_diff:+.2f} | {multi_t} | {single_t} | {t_diff:+.1f} | {riesgos_m} | {riesgos_s} | {ganador} |")
    
    lines.append("")
    
    # Agregar fila de promedio
    multi_avg_q = global_comp.get("averages", {}).get("multi_agent", {}).get("quality", 0)
    single_avg_q = global_comp.get("averages", {}).get("single_agent", {}).get("quality", 0)
    avg_t = global_comp.get("averages", {}).get("multi_agent", {}).get("tokens", 0)
    avg_st = global_comp.get("averages", {}).get("single_agent", {}).get("tokens", 0)
    avg_t_diff = global_comp.get("differences", {}).get("tokens", 0)
    avg_q_diff = global_comp.get("differences", {}).get("quality", 0)
    ganador_global = "multi-agent" if multi_avg_q > single_avg_q else "single-agent"
    
    lines.append(f"| **Promedio** | **---** | **---** | **{multi_avg_q:.2f}** | **{single_avg_q:.2f}** | **{avg_q_diff:+.2f}** | **{avg_t}** | **{avg_st}** | **{avg_t_diff:+.1f}** | **---** | **---** | **{ganador_global}** |")
    
    lines.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    return output_path


def main():
    """Punto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comparar single-agent vs multi-agent")
    parser.add_argument("--questions", default="eval/questions.json", help="Ruta al archivo de preguntas")
    parser.add_argument("--auto-approve", action="store_true", help="Automáticamente aprobar acciones SENSIBLES")
    parser.add_argument("--model", default="qwen2.5:3b", help="Modelo de Ollama a usar")
    parser.add_argument("--output", default="output", help="Directorio de salida")
    parser.add_argument("--generate-all", action="store_true", help="Generar todos los archivos de salida")
    
    args = parser.parse_args()
    
    # Cargar preguntas
    questions = load_questions(args.questions)
    
    # Ejecutar comparación
    results = run_comparison(questions, auto_approve=args.auto_approve, model=args.model)
    
    # Guardar resultados
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    save_results(results, os.path.join(output_dir, "comparison_results.json"))
    
    # Generar tabla Markdown
    md_path = generate_markdown_table(results, os.path.join(output_dir, "comparison_table.md"))
    print(f"Tabla Markdown generada: {md_path}")
    
    # Mostrar resumen final
    global_comp = results.get("global_comparison", {})
    print(f"\n{'='*70}")
    print("RESUMEN FINAL DE COMPARACIÓN")
    print(f"{'='*70}")
    print(f"Preguntas evaluadas: {global_comp.get('total_questions', 0)}")
    print(f"Calidad multi-agent: {global_comp.get('averages', {}).get('multi_agent', {}).get('quality', 0):.2f}")
    print(f"Calidad single-agent: {global_comp.get('averages', {}).get('single_agent', {}).get('quality', 0):.2f}")
    print(f"Diferencia de calidad: {global_comp.get('differences', {}).get('quality', 0):+.2f}")
    print(f"Diferencia de tokens: {global_comp.get('differences', {}).get('tokens', 0):+.0f}")
    print(f"Diferencia de latencia: {global_comp.get('differences', {}).get('latency', 0):+.2f}s")
    print(f"Multi-agent wins: {global_comp.get('wins', {}).get('multi-agent', 0)}/{global_comp.get('total_questions', 0)}")
    print(f"Single-agent wins: {global_comp.get('wins', {}).get('single-agent', 0)}/{global_comp.get('total_questions', 0)}")
    print(f"Multi-agent detecta más riesgos: {global_comp.get('risk_detection', {}).get('multi_detects_more', False)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()