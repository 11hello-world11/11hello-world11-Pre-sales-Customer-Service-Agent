import chromadb
from chromadb.utils import embedding_functions
import dashscope
from dashscope import TextEmbedding
from http import HTTPStatus
from langchain_core.tools import tool
from typing import List
import os
from config import (
    BASE_DIR,
    CHROMA_PATH,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    DASHSCOPE_API_KEY
)


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


@tool
def search_local_knowledge(query: str) -> str:
    """
    Search for answers in local knowledge base (RAG) using semantic search.
    Useful for answering general questions about product features, common issues, and opening requirements.
    
    Args:
        query: The search query string.
    """
    try:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn = AliyunEmbeddingFunction()
        collection = client.get_or_create_collection(
            name="qa_knowledge_base",
            embedding_function=embedding_fn
        )
        if collection.count() == 0:
            return "知识库为空，请先构建：运行 python build_rag.py"
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        if not results['documents'] or not results['documents'][0]:
            return "未在知识库中找到相关信息。"
        context_str = ""
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i]['source']
            context_str += f"--- Source: {source} ---\n{doc}\n\n"
        return context_str
    except Exception as e:
        hint = ""
        if "Embedding model load failed" in str(e) or "Server disconnected" in str(e):
            hint = "；请检查 DASHSCOPE_API_KEY 是否正确配置"
        return f"Error searching knowledge base: {str(e)}{hint}"


@tool
def ask_supervisor_approval(application_details: str) -> str:
    """
    Simulate sending a price application to a supervisor (the human user) and waiting for approval.
    Use this tool when the customer requests a price lower than the calculated price.
    
    Args:
        application_details: A formatted string containing the application details (Size, Config, Price, etc.).
    """
    print("\n" + "="*50)
    print("📢 【向主管申请价格】")
    print(application_details)
    print("="*50 + "\n")
    
    approval = input("主管请批复 (同意/拒绝/其他指令): ")
    return f"主管批复: {approval}"
