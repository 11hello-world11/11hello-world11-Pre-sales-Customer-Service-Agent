import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    BASE_DIR = os.getcwd()

CHROMA_PATH = os.path.join(BASE_DIR, "chromadb")
QA_TXT_DIR = os.path.join(BASE_DIR, "QA_txt")
IMG_DIR = os.path.join(BASE_DIR, "img")
VID_DIR = os.path.join(BASE_DIR, "video")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SESSION_DIR = os.path.join(BASE_DIR, "sessions")

EMBEDDING_MODEL_NAME = "text-embedding-v4"
EMBEDDING_DIMENSION = 1024

DEEPSEEK_API_KEY: Optional[str] = os.environ.get("DEEPSEEK_API_KEY")
DASHSCOPE_API_KEY: Optional[str] = os.environ.get("DASHSCOPE_API_KEY")
AGENT_VERBOSE: bool = str(os.environ.get("AGENT_VERBOSE", "")).lower() in ("1", "true", "yes")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TEMPERATURE = 0.0

SLIDING_WINDOW_SIZE = 15
SQL_CACHE_CAPACITY = 256
SCHEMA_CACHE_CAPACITY = 64

LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def validate_config() -> None:
    errors = []
    
    if not DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY is not set in .env file")
    
    if not DASHSCOPE_API_KEY:
        errors.append("DASHSCOPE_API_KEY is not set in .env file")
    
    if not os.path.exists(QA_TXT_DIR):
        errors.append(f"QA text directory not found: {QA_TXT_DIR}")
    
    if errors:
        error_msg = "\n".join([f"- {err}" for err in errors])
        raise RuntimeError(f"Configuration validation failed:\n{error_msg}")


def get_config_summary() -> str:
    summary = []
    summary.append(f"Base Directory: {BASE_DIR}")
    summary.append(f"ChromaDB Path: {CHROMA_PATH}")
    summary.append(f"QA Text Directory: {QA_TXT_DIR}")
    summary.append(f"Image Directory: {IMG_DIR}")
    summary.append(f"Video Directory: {VID_DIR}")
    summary.append(f"Embedding Model: {EMBEDDING_MODEL_NAME}")
    summary.append(f"Embedding Dimension: {EMBEDDING_DIMENSION}")
    summary.append(f"DeepSeek Model: {DEEPSEEK_MODEL}")
    summary.append(f"Verbose Mode: {'ON' if AGENT_VERBOSE else 'OFF'}")
    return "\n".join(summary)
