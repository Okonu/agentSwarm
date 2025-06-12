import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import json
import re
from dataclasses import asdict

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

        self.text_collection = self.client.get_or_create_collection(
            name="infinitepay_text",
            metadata={"hnsw:space": "cosine"}
        )

        self.pricing_collection = self.client.get_or_create_collection(
            name="infinitepay_pricing",
            metadata={"hnsw:space": "cosine"}
        )

        self.structured_collection = self.client.get_or_create_collection(
            name="infinitepay_structured",
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents_enhanced(self, documents: List[Dict[str, Any]]):
        try:
            text_docs = []
            pricing_docs = []
            structured_docs = []

            for doc_idx, doc in enumerate(documents):
                if "chunks" in doc and doc["chunks"]:
                    for chunk_idx, chunk in enumerate(doc["chunks"]):
                        doc_id = f"doc_{doc_idx}_chunk_{chunk_idx}_{hash(doc['url'])}"

                        metadata = {
                            "url": doc["url"],
                            "title": doc.get("title", ""),
                            "chunk_type": chunk.chunk_type,
                            "chunk_index": chunk_idx,
                            **chunk.metadata
                        }

                        if chunk.chunk_type == "pricing_table":
                            pricing_docs.append({
                                "id": doc_id,
                                "content": chunk.content,
                                "metadata": metadata,
                                "pricing_data": chunk.pricing_data
                            })
                        elif chunk.chunk_type in ["feature_list", "header"]:
                            structured_docs.append({
                                "id": doc_id,
                                "content": chunk.content,
                                "metadata": metadata
                            })
                        else:
                            text_docs.append({
                                "id": doc_id,
                                "content": chunk.content,
                                "metadata": metadata
                            })
                else:
                    doc_id = f"doc_{doc_idx}_{hash(doc['url'])}"
                    text_content = f"{doc.get('title', '')} {doc.get('text', '')}"

                    metadata = {
                        "url": doc["url"],
                        "title": doc.get("title", ""),
                        "chunk_type": "full_document",
                        "meta_description": doc.get("meta_description", ""),
                        "headings": str(doc.get("headings", [])),
                    }

                    text_docs.append({
                        "id": doc_id,
                        "content": text_content,
                        "metadata": metadata
                    })

            if text_docs:
                await self._add_to_collection(self.text_collection, text_docs)
                logger.info(f"Added {len(text_docs)} text documents")

            if pricing_docs:
                await self._add_to_collection(self.pricing_collection, pricing_docs, include_pricing=True)
                logger.info(f"Added {len(pricing_docs)} pricing documents")

            if structured_docs:
                await self._add_to_collection(self.structured_collection, structured_docs)
                logger.info(f"Added {len(structured_docs)} structured documents")

        except Exception as e:
            logger.error(f"Error adding enhanced documents: {str(e)}")
            raise

    async def _add_to_collection(self, collection, docs: List[Dict], include_pricing: bool = False):
        if not docs:
            return

        doc_ids = []
        doc_texts = []
        doc_metadatas = []

        for doc in docs:
            doc_ids.append(doc["id"])
            doc_texts.append(doc["content"])

            metadata = doc["metadata"].copy()

            if include_pricing and "pricing_data" in doc and doc["pricing_data"]:
                metadata["has_pricing_data"] = True
                metadata["pricing_count"] = len(doc["pricing_data"])
                metadata["pricing_json"] = json.dumps([asdict(p) for p in doc["pricing_data"]])

            doc_metadatas.append(metadata)

        embeddings = self.embedding_model.encode(doc_texts)

        collection.add(
            ids=doc_ids,
            documents=doc_texts,
            metadatas=doc_metadatas,
            embeddings=embeddings.tolist()
        )

    async def search_enhanced(self, query: str, k: int = 5, search_type: str = "all") -> List[Dict[str, Any]]:
        try:
            query_lower = query.lower()
            is_pricing_query = any(keyword in query_lower for keyword in [
                'fee', 'rate', 'cost', 'price', 'charge', '%', 'percent', 'how much'
            ])

            query_embedding = self.embedding_model.encode([query])

            all_results = []

            if is_pricing_query or search_type in ["all", "pricing"]:
                pricing_results = self.pricing_collection.query(
                    query_embeddings=query_embedding.tolist(),
                    n_results=min(k, 3),
                    include=["documents", "metadatas", "distances"]
                )
                all_results.extend(self._format_results(pricing_results, "pricing"))

            if search_type in ["all", "structured"]:
                structured_results = self.structured_collection.query(
                    query_embeddings=query_embedding.tolist(),
                    n_results=min(k, 2),
                    include=["documents", "metadatas", "distances"]
                )
                all_results.extend(self._format_results(structured_results, "structured"))

            if search_type in ["all", "text"]:
                text_results = self.text_collection.query(
                    query_embeddings=query_embedding.tolist(),
                    n_results=k,
                    include=["documents", "metadatas", "distances"]
                )
                all_results.extend(self._format_results(text_results, "text"))

            unique_results = self._deduplicate_results(all_results)
            unique_results.sort(key=lambda x: x["similarity"], reverse=True)

            return unique_results[:k]

        except Exception as e:
            logger.error(f"Error in enhanced search: {str(e)}")
            return []

    def _format_results(self, results, collection_type: str) -> List[Dict[str, Any]]:
        formatted_results = []

        if not results['ids'] or not results['ids'][0]:
            return formatted_results

        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            result = {
                "document": results['documents'][0][i],
                "metadata": metadata,
                "similarity": 1 - results['distances'][0][i],
                "collection_type": collection_type,
                "chunk_type": metadata.get("chunk_type", "unknown")
            }

            if metadata.get("has_pricing_data") and metadata.get("pricing_json"):
                try:
                    result["pricing_data"] = json.loads(metadata["pricing_json"])
                except:
                    pass

            formatted_results.append(result)

        return formatted_results

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result["metadata"].get("url", "")
            content_hash = hash(result["document"][:100])

            identifier = f"{url}_{content_hash}"
            if identifier not in seen_urls:
                seen_urls.add(identifier)
                unique_results.append(result)

        return unique_results

    def extract_pricing_insights(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        pricing_insights = {
            "has_pricing_data": False,
            "payment_methods": set(),
            "rate_ranges": {},
            "volume_tiers": set(),
            "specific_rates": []
        }

        for result in results:
            if "pricing_data" in result:
                pricing_insights["has_pricing_data"] = True

                for pricing in result["pricing_data"]:
                    payment_method = pricing.get("payment_method", "unknown")
                    rate_numeric = pricing.get("rate_numeric")

                    pricing_insights["payment_methods"].add(payment_method)

                    if rate_numeric is not None:
                        if payment_method not in pricing_insights["rate_ranges"]:
                            pricing_insights["rate_ranges"][payment_method] = {"min": rate_numeric, "max": rate_numeric}
                        else:
                            current = pricing_insights["rate_ranges"][payment_method]
                            current["min"] = min(current["min"], rate_numeric)
                            current["max"] = max(current["max"], rate_numeric)

                        pricing_insights["specific_rates"].append({
                            "payment_method": payment_method,
                            "rate": pricing.get("rate", ""),
                            "rate_numeric": rate_numeric,
                            "conditions": pricing.get("conditions", ""),
                            "volume_tier": pricing.get("volume_tier")
                        })

                    if pricing.get("volume_tier"):
                        pricing_insights["volume_tiers"].add(pricing["volume_tier"])

        pricing_insights["payment_methods"] = list(pricing_insights["payment_methods"])
        pricing_insights["volume_tiers"] = list(pricing_insights["volume_tiers"])

        return pricing_insights

    def get_collection_info(self) -> Dict[str, Any]:
        try:
            return {
                "text_documents": self.text_collection.count(),
                "pricing_documents": self.pricing_collection.count(),
                "structured_documents": self.structured_collection.count(),
                "document_count": (
                        self.text_collection.count() +
                        self.pricing_collection.count() +
                        self.structured_collection.count()
                ),
                "collections": ["text", "pricing", "structured"]
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"document_count": 0, "collections": [], "error": str(e)}