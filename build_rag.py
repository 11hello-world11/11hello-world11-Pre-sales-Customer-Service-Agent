import os
import shutil
from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
import dashscope
from dashscope import TextEmbedding
from http import HTTPStatus
from dotenv import load_dotenv
from config import (
    BASE_DIR,
    CHROMA_PATH,
    QA_TXT_DIR,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    DASHSCOPE_API_KEY
)

load_dotenv()


class AliyunEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, 
                 dimension: int = EMBEDDING_DIMENSION,
                 api_key: str = DASHSCOPE_API_KEY):
        self.model_name = model_name
        self.dimension = dimension
        self.api_key = api_key
        if self.api_key:
            dashscope.api_key = self.api_key
        else:
            raise ValueError("DASHSCOPE_API_KEY is required. Please set it in .env file.")
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        all_embeddings = []
        
        for text in input:
            resp = TextEmbedding.call(
                model=self.model_name,
                input=text,
                dimension=self.dimension
            )
            
            if resp.status_code == HTTPStatus.OK:
                embedding = resp.output['embeddings'][0]['embedding']
                all_embeddings.append(embedding)
            else:
                raise RuntimeError(f"Embedding request failed: {resp}")
        
        return all_embeddings


def load_documents(directory: str) -> List[Dict]:
    documents = []
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} does not exist.")
        return documents
        
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                chunks = content.split("\n\n")
                for i, chunk in enumerate(chunks):
                    chunk = chunk.strip()
                    if chunk:
                        documents.append({
                            "id": f"{filename}_{i}",
                            "text": chunk,
                            "source": filename
                        })
    return documents


def init_chromadb():
    if not os.path.exists(CHROMA_PATH):
        os.makedirs(CHROMA_PATH)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
    embedding_fn = AliyunEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="qa_knowledge_base",
        embedding_function=embedding_fn
    )
    return collection


def build_knowledge_base():
    print("Building knowledge base...")
    
    docs = load_documents(QA_TXT_DIR)
    print(f"Loaded {len(docs)} chunks from {QA_TXT_DIR}")
    
    if not docs:
        print("No documents found. Exiting.")
        return

    collection = init_chromadb()
    
    if collection.count() == 0:
        print("Adding documents to ChromaDB...")
        ids = [doc["id"] for doc in docs]
        documents = [doc["text"] for doc in docs]
        metadatas = [{"source": doc["source"]} for doc in docs]
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"Successfully added {len(docs)} documents.")
    else:
        print(f"Collection already contains {collection.count()} documents. Skipping insertion.")


if __name__ == "__main__":
    build_knowledge_base()
