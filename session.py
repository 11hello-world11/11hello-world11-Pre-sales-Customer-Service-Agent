import json
import os
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, BaseMessage
from config import BASE_DIR


def get_session_dir():
    return os.path.join(BASE_DIR, "sessions")


def get_session_path(session_id):
    return os.path.join(get_session_dir(), f"{session_id}.json")


def message_to_dict(message):
    message_dict = {
        "type": message.__class__.__name__,
        "content": message.content,
    }
    if hasattr(message, "tool_calls") and message.tool_calls:
        message_dict["tool_calls"] = message.tool_calls
    if hasattr(message, "tool_call_id") and message.tool_call_id:
        message_dict["tool_call_id"] = message.tool_call_id
    return message_dict


def dict_to_message(message_dict):
    msg_type = message_dict["type"]
    content = message_dict["content"]
    
    if msg_type == "HumanMessage":
        return HumanMessage(content=content)
    elif msg_type == "AIMessage":
        msg = AIMessage(content=content)
        if "tool_calls" in message_dict:
            msg.tool_calls = message_dict["tool_calls"]
        return msg
    elif msg_type == "ToolMessage":
        tool_call_id = message_dict.get("tool_call_id", "")
        return ToolMessage(content=content, tool_call_id=tool_call_id)
    elif msg_type == "SystemMessage":
        return SystemMessage(content=content)
    else:
        return HumanMessage(content=content)


def save_session(session_id, messages, key_info=None):
    session_dir = get_session_dir()
    os.makedirs(session_dir, exist_ok=True)
    
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": [message_to_dict(msg) for msg in messages],
        "key_info": key_info or {}
    }
    file_path = get_session_path(session_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)


def load_session(session_id):
    file_path = get_session_path(session_id)
    if not os.path.exists(file_path):
        return [], {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)
    
    messages = [dict_to_message(msg) for msg in session_data.get("messages", [])]
    key_info = session_data.get("key_info", {})
    return messages, key_info


def list_sessions():
    session_dir = get_session_dir()
    if not os.path.exists(session_dir):
        return []
    
    sessions = []
    for filename in os.listdir(session_dir):
        if filename.endswith(".json"):
            session_id = filename[:-5]
            file_path = os.path.join(session_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                sessions.append({
                    "session_id": session_id,
                    "created_at": session_data.get("created_at", ""),
                    "message_count": len(session_data.get("messages", []))
                })
            except Exception:
                pass
    sessions.sort(key=lambda x: x["created_at"], reverse=True)
    return sessions
