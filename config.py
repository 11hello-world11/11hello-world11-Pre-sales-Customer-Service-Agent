import os
from dotenv import load_dotenv

load_dotenv()

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    BASE_DIR = os.getcwd()

CHROMA_PATH = os.path.join(BASE_DIR, "chromadb")
QA_TXT_DIR = os.path.join(BASE_DIR, "QA_txt")
EMBEDDING_MODEL_NAME = "text-embedding-v4"
EMBEDDING_DIMENSION = 1024
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")
