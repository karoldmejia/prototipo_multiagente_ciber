"""RAG Retriever - Recupera documentos relevantes para el contexto del LLM."""

import os
from typing import List, Dict, Any, Optional

from .indexer import RAGIndexer, get_embedding


class RAGRetriever:
    """Clase para recuperar documentos relevantes basándose en consultas."""
    
    def __init__(self, chroma_path: str = None, collection_name: str = "tech_docs"):
        if chroma_path is None:
            chroma_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        self.indexer = RAGIndexer(chroma_path, collection_name)
    
    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Busca documentos relevantes para la consulta."""
        results = self.indexer.retrieve(query, n_results=n_results)
        
        formatted_results = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        
        for i, doc in enumerate(documents):
            formatted_results.append({
                "content": doc,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "id": ids[i] if i < len(ids) else f"unknown_{i}"
            })
        
        return formatted_results
    
    def get_context(self, query: str, max_chars: int = 2000) -> str:
        """Obtiene un contexto formateado para incluir en prompts."""
        results = self.search(query, n_results=5)
        context_parts = []
        
        for i, result in enumerate(results):
            content = result["content"]
            # Truncar si es muy largo
            if len(content) > max_chars // len(results):
                content = content[:max_chars // len(results)] + "..."
            context_parts.append(f"--- Documento {i+1} ---\n{content}")
        
        return "\n\n".join(context_parts)


def test_retriever():
    """Función de prueba para el retriever."""
    print("Probando retriever RAG...")
    retriever = RAGRetriever()
    
    queries = [
        "politicas de seguridad",
        "inyección en logs",
        "fuga de prompt"
    ]
    
    for query in queries:
        print(f"\nConsulta: '{query}'")
        context = retriever.get_context(query, max_chars=1500)
        print(f"Contexto generado (first 200 chars): {context[:200]}...")
        
        results = retriever.search(query, n_results=3)
        for i, r in enumerate(results):
            print(f"  Resultado {i+1}: {r['content'][:80]}...")


if __name__ == "__main__":
    test_retriever()