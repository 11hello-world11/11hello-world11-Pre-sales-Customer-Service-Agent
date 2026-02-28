import os
import uuid
import hashlib
from typing import List, Tuple, Dict
import chromadb
from dotenv import load_dotenv
from config import BASE_DIR, CHROMA_PATH
from tools import AliyunEmbeddingFunction


IMG_DIR = os.path.join(BASE_DIR, "img")
VID_DIR = os.path.join(BASE_DIR, "video")

try:
    from media_tags import MEDIA_TAGS
except Exception:
    MEDIA_TAGS = {}


def _stable_id(prefix: str, path: str) -> str:
    try:
        st = os.stat(path)
        raw = f"{path}|{st.st_size}|{int(st.st_mtime)}"
    except Exception:
        raw = f"{path}|{uuid.uuid4()}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{h}"


def _list_media(root: str, exts: Tuple[str, ...]) -> List[str]:
    items = []
    if not os.path.exists(root):
        return items
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(exts):
                items.append(os.path.join(dirpath, name))
    return items


def _image_proxy_text(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return f"图片 {name}"


def _video_proxy_text(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return f"视频 {name}"


def _merge_tags(base_tags: List[str], extra_tags: List[str]) -> List[str]:
    out = []
    seen = set()
    for t in (base_tags or []) + (extra_tags or []):
        if not t:
            continue
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _resolve_tags(modality: str, root_dir: str, path: str) -> List[str]:
    base = os.path.basename(path)
    # 获取相对路径，例如 "a/b/c"
    rel_path = os.path.relpath(os.path.dirname(path), root_dir)
    if rel_path == ".":
        rel_path = ""
    else:
        rel_path = rel_path.replace("\\", "/")

    cfg = (MEDIA_TAGS or {}).get(modality, {}) if isinstance(MEDIA_TAGS, dict) else {}
    
    # 1. 基础 default 标签
    tags = list(cfg.get("default") or [])

    # 2. 逐级继承 folders 标签
    # 例如 rel_path="a/b"，则依次查找 folders["a"] 和 folders["a/b"]
    folders = cfg.get("folders") or {}
    if isinstance(folders, dict) and rel_path:
        parts = rel_path.split("/")
        current_path = ""
        for part in parts:
            if current_path:
                current_path = f"{current_path}/{part}"
            else:
                current_path = part
            
            if current_path in folders:
                tags = _merge_tags(tags, folders.get(current_path) or [])

    # 3. 具体文件 files 标签
    files = cfg.get("files") or {}
    if isinstance(files, dict) and base in files:
        tags = _merge_tags(tags, files.get(base) or [])

    # 如果完全没有配置命中，才回退到自动推断
    # 注意：一旦命中了 default/folders/files 任意一个，tags 就非空了
    if not tags:
        if modality == "image":
            return _infer_image_tags(path)
        if modality == "video":
            return _infer_video_tags(path)
            
    return tags

def _infer_image_tags(path: str) -> List[str]:
    base = os.path.basename(path)
    tags = ["一体机", "图片"]
    lower = base.lower()
    if "会议" in base:
        tags.append("会议场景")
    if "教学" in base:
        tags.append("教学场景")
    return tags


def _infer_video_tags(path: str) -> List[str]:
    base = os.path.basename(path)
    tags = ["一体机", "视频", "演示"]
    if "双系统" in base:
        tags += ["双系统", "切换"]
    return tags


def _build_doc(title: str, tags: List[str]) -> str:
    tag_str = "，".join(tags)
    return f"{title}\n标签：{tag_str}"


def _upsert_by_ids(collection, ids: List[str], documents: List[str], metadatas: List[Dict]):
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def _init_collection(client: chromadb.PersistentClient, name: str):
    emb_fn = AliyunEmbeddingFunction()
    return client.get_or_create_collection(name=name, embedding_function=emb_fn)


def build_multimodal_knowledge_base():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    img_collection = _init_collection(client, "kb_image")
    vid_collection = _init_collection(client, "kb_video")

    img_paths = _list_media(IMG_DIR, (".jpg", ".jpeg", ".png", ".webp"))
    vid_paths = _list_media(VID_DIR, (".mp4", ".mov", ".mkv", ".avi"))

    if img_paths:
        ids = []
        docs = []
        metas = []
        for p in img_paths:
            title = _image_proxy_text(p)
            tags = _resolve_tags("image", IMG_DIR, p)
            ids.append(_stable_id("img", p))
            docs.append(_build_doc(title, tags))
            metas.append({"path": p, "modality": "image", "title": title, "tags": tags})
        _upsert_by_ids(img_collection, ids, docs, metas)

    if vid_paths:
        ids = []
        docs = []
        metas = []
        for p in vid_paths:
            title = _video_proxy_text(p)
            tags = _resolve_tags("video", VID_DIR, p)
            ids.append(_stable_id("vid", p))
            docs.append(_build_doc(title, tags))
            metas.append({"path": p, "modality": "video", "title": title, "tags": tags})
        _upsert_by_ids(vid_collection, ids, docs, metas)


if __name__ == "__main__":
    load_dotenv()
    build_multimodal_knowledge_base()
