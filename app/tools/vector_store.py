import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_directory: str, embedding_model: str):
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self.embedding_model = SentenceTransformer(embedding_model)

        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="infinitepay_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the vector store"""
        try:
            doc_ids = []
            doc_texts = []
            doc_metadatas = []

            for i, doc in enumerate(documents):
                doc_id = f"doc_{i}_{hash(doc['url'])}"
                doc_ids.append(doc_id)

                text_content = f"{doc.get('title', '')} {doc.get('text', '')}"
                doc_texts.append(text_content)

                metadata = {
                    "url": doc["url"],
                    "title": doc.get("title", ""),
                    "meta_description": doc.get("meta_description", ""),
                    "headings": str(doc.get("headings", [])),
                }
                doc_metadatas.append(metadata)

            embeddings = self.embedding_model.encode(doc_texts)

            self.collection.add(
                ids=doc_ids,
                documents=doc_texts,
                metadatas=doc_metadatas,
                embeddings=embeddings.tolist()
            )

            logger.info(f"Added {len(documents)} documents to vector store")

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise

    async def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            query_embedding = self.embedding_model.encode([query])

            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            search_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity": 1 - results['distances'][0][i],
                }
                search_results.append(result)

            return search_results

        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {"document_count": count, "collection_name": "infinitepay_knowledge"}
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"document_count": 0, "collection_name": "infinitepay_knowledge"}