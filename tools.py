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
def search_media_asset(query: str) -> str:
    """
    Search for a related local media asset (image/video) by text query.
    Returns best matched modality and absolute file path for sending to user.
    """
    try:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn = AliyunEmbeddingFunction()

        img_col = client.get_or_create_collection(name="kb_image", embedding_function=embedding_fn)
        vid_col = client.get_or_create_collection(name="kb_video", embedding_function=embedding_fn)

        if img_col.count() == 0 and vid_col.count() == 0:
            return "媒体库为空，请先构建：运行 python build_multimodal_kb.py"

        candidates = []

        if img_col.count() > 0:
            r = img_col.query(query_texts=[query], n_results=1, include=["metadatas", "distances", "documents"])
            if r.get("metadatas") and r["metadatas"][0]:
                candidates.append(
                    {
                        "modality": "image",
                        "path": r["metadatas"][0][0].get("path", ""),
                        "score": float(r.get("distances", [[0.0]])[0][0]),
                        "title": r["metadatas"][0][0].get("title", ""),
                    }
                )

        if vid_col.count() > 0:
            r = vid_col.query(query_texts=[query], n_results=1, include=["metadatas", "distances", "documents"])
            if r.get("metadatas") and r["metadatas"][0]:
                candidates.append(
                    {
                        "modality": "video",
                        "path": r["metadatas"][0][0].get("path", ""),
                        "score": float(r.get("distances", [[0.0]])[0][0]),
                        "title": r["metadatas"][0][0].get("title", ""),
                    }
                )

        if not candidates:
            return "未在媒体库中找到相关文件。"

        best = sorted(candidates, key=lambda x: x["score"])[0]
        return f"modality={best['modality']}\npath={best['path']}\ntitle={best['title']}\ndistance={best['score']}"
    except Exception as e:
        hint = ""
        if "Embedding model load failed" in str(e) or "Server disconnected" in str(e):
            hint = "；请检查 DASHSCOPE_API_KEY 是否正确配置"
        return f"Error searching media asset: {str(e)}{hint}"


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


@tool
def ask_installation_approval(installation_details: str) -> str:
    """
    提交包安装申请至主管并等待批复。
    当用户需要上门安装/包安装等服务时使用，内容需包含尺寸、配置、地址、时间窗等信息。
    Args:
        installation_details: 格式化后的申请详情文本。
    """
    print("\n" + "="*50)
    print("📢 【向主管申请包安装】")
    print(installation_details)
    print("="*50 + "\n")
    approval = input("主管请批复 (同意/拒绝/其他指令): ")
    return f"主管批复: {approval}"


@tool
def format_application_details(
    申请类型: str,
    尺寸: str,
    配置: str,
    支架: str,
    台数: int,
    赠品: str,
    已报价格: str,
    底价: str,
    客户要求: str,
    是否含税: str,
    备注: str = ""
) -> str:
    """
    生成统一的主管申请详情文本（价格申请与包安装申请通用）。
    使用相同字段，便于直接传给 ask_supervisor_approval 或 ask_installation_approval。
    Args:
        申请类型: 如 "申请价格" 或 "申请包安装"
        其余字段同系统提示中的申请格式
    Returns:
        标准化的申请详情字符串
    """
    lines = [
        f"**{申请类型}**",
        f"**尺寸:** {尺寸}",
        f"**配置:** {配置}",
        f"**支架:** {支架}",
        f"**台数:** {台数}",
        f"**赠品:** {赠品}",
        f"**已报价格:** {已报价格}",
        f"**底价:** {底价}",
        f"**客户要求:** {客户要求}",
        f"**是否含税:** {是否含税}",
    ]
    if 备注:
        lines.append(f"**备注:** {备注}")
    return "\n".join(lines)
