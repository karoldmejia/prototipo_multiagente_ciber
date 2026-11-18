"""RAG Indexer - Indexa documentos técnicos para recuperación semántica."""

import os
import re
from typing import List, Dict, Any

import ollama
import chromadb

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


def get_embedding(text: str, model: str = "nomic-embed-text") -> List[float]:
    """Obtiene embedding de un texto usando Ollama."""
    response = ollama.embed(model=model, input=text)
    return response["embeddings"][0]


class RAGIndexer:
    """Clase para indexar documentos en ChromaDB."""
    
    def __init__(self, chroma_path: str = CHROMA_PATH, collection_name: str = "tech_docs"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Divide el texto en fragmentos con superposición."""
        chunks = []
        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks
    
    def index_document(self, file_path: str, metadata: Dict[str, Any] = None) -> List[str]:
        """Indexa un documento individual."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        chunks = self.chunk_text(text)
        embeddings = []
        chunk_ids = []
        
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            embeddings.append(embedding)
            chunk_id = f"{os.path.basename(file_path)}_{i}"
            chunk_ids.append(chunk_id)
        
        if metadata is None:
            metadata = {"source": os.path.basename(file_path)}
        
        self.collection.add(
            embeddings=embeddings,
            ids=chunk_ids,
            documents=chunks,
            metadatas=[metadata] * len(chunks)
        )
        
        return chunk_ids
    
    def index_all_documents(self) -> Dict[str, List[str]]:
        """Indexa todos los documentos de la carpeta docs."""
        results = {}
        for filename in sorted(os.listdir(DOCS_DIR)):
            if filename.endswith(".md"):
                file_path = os.path.join(DOCS_DIR, filename)
                chunk_ids = self.index_document(file_path)
                results[filename] = chunk_ids
        return results
    
    def retrieve(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """Recupera los documentos más relevantes para una consulta."""
        query_embedding = get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results


def test_indexing():
    """Función de prueba para verificar que el indexado funciona."""
    indexer = RAGIndexer()
    print("Indexando documentos...")
    results = indexer.index_all_documents()
    for filename, ids in results.items():
        print(f"  {filename}: {len(ids)} chunks indexados")
    
    # Test de recuperación
    print("\nTest de recuperación:")
    query = "politicas de seguridad"
    results = indexer.retrieve(query)
    print(f"  Consulta: '{query}'")
    if results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            print(f"  {i+1}. {doc[:100]}...")
    else:
        print("  No se encontraron resultados.")


if __name__ == "__main__":
    test_indexing()