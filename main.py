"""Punto de entrada principal para el prototipo multiagente con RAG, herramientas y MCP."""

import argparse
import json
import os
import sys
from typing import Dict, Any

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator
from agents.surface import SurfaceAgent
from agents.attack_sim import AttackSimulationAgent
from agents.evidence import EvidenceAgent
from mcp_server import main as mcp_main


def demo_mode():
    """Modo demo: ejecuta el flujo multiagente sobre una misión de ejemplo."""
    print("\n" + "="*60)
    print("MODOS DEMOSTRACIÓN - Flujo Multiagente Orquestado")
    print("="*60 + "\n")
    
    # Misión de ejemplo
    mission = "Consulta las políticas de seguridad y busca cualquier indicio de inyección en los logs"
    
    print(f"Misión: {mission}")
    print()
    
    # 1. Superficie: inventariar configuración y evaluar riesgos
    print("--- Paso 1: Agente de Superficie ---")
    surface = SurfaceAgent(model_name="qwen2.5:3b")
    diagnostic = surface.run_diagnostic(mission)
    print()
    
    # 2. Orquestador: descomponer misión
    print("--- Paso 2: Orquestador ---")
    orchestrator = Orchestrator(model_name="qwen2.5:3b")
    decomposition = orchestrator.decompose_mission(mission)
    print()
    
    # 3. Ejecutar pasos con capas determinísticas
    print("--- Paso 3: Ejecución con Motor Determinístico ---")
    result = orchestrator.execute_steps(mission, auto_approve=True)
    print()
    
    # 4. Evaluación y dictamen final
    print("--- Paso 4: Agente de Evidencia y Dictamen Final ---")
    dictamen = result["dictamen"]
    
    # Guardar dictamen
    os.makedirs("output", exist_ok=True)
    with open("output/dictamen.json", "w", encoding="utf-8") as f:
        json.dump(dictamen, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Dictamen guardado en output/dictamen.json")
    print(f"\nVerdictó final: {dictamen['overall_verdict']}")
    print(f"Mejor configuración: {dictamen['comparison']['better_configuration'].upper()}")
    print()
    
    # Mostrar resumen de riesgos
    risk_summary = dictamen.get("risk_analysis", {}).get("summary", "No available")
    print(f"Resumen de riesgos: {risk_summary}")
    print()
    
    # Mostrar métricas
    metrics = dictamen.get("metrics", {})
    print(f"Métricas recopiladas:")
    print(f"  - Tokens de entrada: {metrics.get('tokens_input', 0)}")
    print(f"  - Tokens de salida: {metrics.get('tokens_output', 0)}")
    print(f"  - Latencia total: {metrics.get('latency_total', 0):.2f}s")
    print(f"  - Pasos ejecutados: {metrics.get('num_steps', 0)}")
    print()
    
    print("="*60)
    print("DEMOSTRACIÓN COMPLETADA")
    print("="*60 + "\n")


def comparison_mode():
    """Modo comparación single-agent vs multi-agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Modo comparación")
    parser.add_argument("--auto-approve", action="store_true", help="Automáticamente aprobar acciones SENSIBLES")
    parser.add_argument("--model", default="qwen2.5:3b", help="Modelo de Ollama a usar")
    args = parser.parse_args()
    
    # Cargar preguntas
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from eval.compare import load_questions, main as comparison_main
    
    # Ejecutar comparación
    questions = load_questions("eval/questions.json")
    comparison_main(questions, auto_approve=args.auto_approve, model=args.model)


def mcp_mode():
    """Modo servidor MCP."""
    print("Iniciando servidor MCP...")
    print("Ejecutando: mcp run mcp_server.py --transport stdio")
    print()
    mcp_main()


def rag_mode():
    """Modo RAG: indexar y consultar documentos."""
    from rag.indexer import RAGIndexer
    from rag.retriever import RAGRetriever
    
    print("=== Modo RAG ===\n")
    
    # Indexar documentos
    print("Indexando documentos...")
    indexer = RAGIndexer()
    results = indexer.index_all_documents()
    print(f"✓ Documentos indexados: {list(results.keys())}")
    print()
    
    # Consultas de prueba
    retriever = RAGRetriever()
    test_queries = [
        "políticas de seguridad",
        "inyección en logs",
        "fuga de prompt"
    ]
    
    for query in test_queries:
        print(f"Consulta: '{query}'")
        results = retriever.search(query, n_results=3)
        print(f"  Hallazgos: {len(results.get('documents', [[]])[0])} documentos")
        if results.get('documents', [[]])[0]:
            for i, doc in enumerate(results['documents'][0][:2]):
                print(f"  {i+1}. {doc[:80]}...")
        print()


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Prototipo de sistema multiagente con RAG, herramientas y MCP opcional"
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="Modos de operación")
    
    # Modo demo
    subparsers.add_parser("demo", help="Ejecutar modo demostración con flujo multiagente")
    
    # Modo comparación
    compare_parser = subparsers.add_parser("compare", help="Comparar single-agent vs multi-agent")
    compare_parser.add_argument("--auto-approve", action="store_true", help="Automáticamente aprobar acciones SENSIBLES")
    compare_parser.add_argument("--model", default="qwen2.5:3b", help="Modelo de Ollama a usar")
    
    # Modo MCP
    subparsers.add_parser("mcp", help="Iniciar servidor MCP local")
    
    # Modo RAG
    subparsers.add_parser("rag", help="Indexar y consultar documentos RAG")
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        demo_mode()
    elif args.mode == "compare":
        comparison_mode()
    elif args.mode == "mcp":
        mcp_mode()
    elif args.mode == "rag":
        rag_mode()
    else:
        # Modo por defecto: demo
        print("Modo no especificado, ejecutando demo por defecto...")
        print()
        demo_mode()


if __name__ == "__main__":
    main()