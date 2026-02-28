from typing import List
import os
import asyncio
import uuid
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage, AIMessage
from tools import search_local_knowledge, search_media_asset, ask_supervisor_approval, ask_installation_approval, format_application_details
from logger import logger
from session import save_session, load_session, list_sessions
from skills.database_query.tools import (
    dbq_price_by_size_config,
    dbq_configs_by_size,
    dbq_i5_i7_price_rows,
    dbq_size_info,
)
import logging

load_dotenv()

VERBOSE = str(os.environ.get("AGENT_VERBOSE", "")).lower() in ("1", "true", "yes")
if not VERBOSE:
    logger.setLevel(logging.WARNING)

def get_sliding_window_messages(messages, window_size=15):
    if len(messages) <= window_size:
        return messages
    
    system_message = None
    other_messages = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_message = msg
        else:
            other_messages.append(msg)
    
    recent_messages = other_messages[-window_size:]
    
    if system_message:
        return [system_message] + recent_messages
    return recent_messages


def extract_key_info_from_messages(messages):
    key_info = {}
    
    for msg in messages:
        if isinstance(msg, AIMessage) and "Final Answer" in msg.content:
            content = msg.content
            
            size_match = re.search(r'尺寸[：:]\s*([^\n]+)', content)
            if size_match:
                key_info["尺寸"] = size_match.group(1).strip()
            
            config_match = re.search(r'配置[：:]\s*([^\n]+)', content)
            if config_match:
                key_info["配置"] = config_match.group(1).strip()
            
            price_match = re.search(r'价格[：:]\s*([^\n]+)', content)
            if price_match:
                key_info["价格"] = price_match.group(1).strip()
            
            stand_match = re.search(r'支架[：:]\s*([^\n]+)', content)
            if stand_match:
                key_info["支架"] = stand_match.group(1).strip()
    
    return key_info


def build_system_prompt_with_key_info(static_prompt, key_info):
    if not key_info:
        return static_prompt
    
    key_info_str = "【已确认的订单信息】\n"
    for key, value in key_info.items():
        key_info_str += f"{key}：{value}\n"
    key_info_str += "\n"
    
    return key_info_str + static_prompt


def filter_orphan_tool_messages(msgs: List):
    ai_tool_ids = set()
    for m in msgs:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tc_id = tc.get("id") if isinstance(tc, dict) else None
                if tc_id:
                    ai_tool_ids.add(tc_id)
    filtered = []
    for m in msgs:
        if isinstance(m, ToolMessage):
            if m.tool_call_id and m.tool_call_id in ai_tool_ids:
                filtered.append(m)
        else:
            filtered.append(m)
    return filtered


async def main():
    logger.info("初始化 LLM...")
    from collections import OrderedDict
    class LRU:
        def __init__(self, capacity=128):
            self.capacity = capacity
            self.map = OrderedDict()
        def get(self, k):
            if k in self.map:
                v = self.map.pop(k)
                self.map[k] = v
                return v
            return None
        def put(self, k, v):
            if k in self.map:
                self.map.pop(k)
            elif len(self.map) >= self.capacity:
                self.map.popitem(last=False)
            self.map[k] = v
    sql_cache = LRU(256)
    schema_cache = LRU(64)
    llm = ChatOpenAI(
        model="deepseek-chat", 
        temperature=0,
        base_url="https://api.deepseek.com",
        api_key=os.environ.get("DEEPSEEK_API_KEY")
    )

    # 会话选择
    print("=" * 50)
    print("欢迎使用智能对话系统")
    print("=" * 50)
    
    sessions = list_sessions()
    session_id = None
    chat_history = None
    key_info = {}
    
    if sessions:
        print("\n可用的历史会话:")
        for i, session in enumerate(sessions, 1):
            print(f"{i}. {session['session_id']} (创建时间: {session['created_at']}, 消息数: {session['message_count']})")
        print(f"{len(sessions) + 1}. 创建新会话")
        
        while True:
            try:
                choice = input("\n请选择会话编号 (回车默认创建新会话): ").strip()
                if not choice:
                    break
                choice_num = int(choice)
                if 1 <= choice_num <= len(sessions):
                    session_id = sessions[choice_num - 1]["session_id"]
                    break
                elif choice_num == len(sessions) + 1:
                    break
                else:
                    print("无效的选择，请重新输入")
            except ValueError:
                print("请输入有效的数字")
    
    if session_id:
        chat_history, key_info = load_session(session_id)
        logger.info(f"加载会话: {session_id}, 消息数: {len(chat_history)}")
        print(f"\n已加载会话: {session_id}")
    else:
        session_id = str(uuid.uuid4())[:8]
        chat_history = []
        key_info = {}
        logger.info(f"创建新会话: {session_id}")
        print(f"\n创建新会话: {session_id}")

    # 2. 准备 MCP Server 配置
    # 读取 mcp-mysql-server 的环境变量文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mysql_server_dir = os.path.join(base_dir, "mcp-mysql-server")
    mysql_env_path = os.path.join(mysql_server_dir, "env")
    
    mysql_env = os.environ.copy()
    if os.path.exists(mysql_env_path):
        logger.info(f"读取 MySQL 环境变量: {mysql_env_path}")
        with open(mysql_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        mysql_env[key.strip()] = value.strip()
                    except ValueError:
                        pass
    
    # 构建启动命令
    script_path = os.path.join(mysql_server_dir, "node_modules", "@fhuang", "mcp-mysql-server", "build", "index.js")
    
    logger.info(f"MCP Server 脚本路径: {script_path}")
    
    # 3. 初始化 MCP Client
    client = MultiServerMCPClient({
        "mysql": {
            "command": "node",
            "args": [script_path],
            "transport": "stdio",
            "env": mysql_env
        }
    })
        
    logger.info("连接 MCP Server 并获取工具...")
    try:
        mcp_tools = await client.get_tools()
        # 合并 MCP 工具和本地工具
        tools = mcp_tools + [
            search_local_knowledge,
            search_media_asset,
            ask_supervisor_approval,
            ask_installation_approval,
            format_application_details,
            dbq_price_by_size_config,
            dbq_configs_by_size,
            dbq_i5_i7_price_rows,
            dbq_size_info,
        ]
        
        logger.info(f"成功获取 {len(tools)} 个工具: {[t.name for t in tools]}")
        logger.info("开始运行智能体... (输入 'exit' 或 'quit' 退出)")
        
        # 读取 System Prompt
        system_prompt_path = os.path.join(base_dir, "system_prompt.txt")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompt_content = f.read()
        else:
            system_prompt_content = "你是一个智能数据库助手。" # 默认 Prompt

        # 如果是新会话，添加 system prompt
        if not chat_history:
            system_prompt = SystemMessage(content=system_prompt_content)
            chat_history = [system_prompt]
        else:
            # 检查是否已有 system prompt
            has_system_prompt = any(isinstance(msg, SystemMessage) for msg in chat_history)
            if not has_system_prompt:
                system_prompt = SystemMessage(content=system_prompt_content)
                chat_history.insert(0, system_prompt)
        
        llm_with_tools = llm.bind_tools(tools)

        while True:
            try:
                user_input = input("\nUser: ")
                logger.info(f"用户输入: {user_input}")
                if user_input.lower() in ["exit", "quit"]:
                    logger.info("用户退出会话")
                    save_session(session_id, chat_history, key_info)
                    logger.info(f"会话已保存: {session_id}")
                    print(f"\n会话已保存: {session_id}")
                    break
            except EOFError:
                logger.warning("收到 EOF，退出会话")
                save_session(session_id, chat_history, key_info)
                logger.info(f"会话已保存: {session_id}")
                break

            # 构造当前对话的消息列表
            # 将用户输入加入历史
            chat_history.append(HumanMessage(content=user_input))
            
            # 使用滑动窗口构建当前消息列表（保留最近15轮 + key_info）
            # 1. 从当前对话历史中提取最新的 key_info
            extracted_key_info = extract_key_info_from_messages(chat_history)
            if extracted_key_info:
                key_info.update(extracted_key_info)
            
            # 2. 构建带 key_info 的动态 system prompt
            dynamic_system_prompt_content = build_system_prompt_with_key_info(
                system_prompt_content, 
                key_info
            )
            dynamic_system_prompt = SystemMessage(content=dynamic_system_prompt_content)
            
            # 3. 获取滑动窗口消息（不包含原始的 system prompt）
            messages_without_system = [msg for msg in chat_history if not isinstance(msg, SystemMessage)]
            sliding_messages = get_sliding_window_messages(messages_without_system, window_size=15)
            
            # 4. 组合：动态 system prompt + 滑动窗口消息
            messages = [dynamic_system_prompt] + sliding_messages
            messages = filter_orphan_tool_messages(messages)
            
            # 内部循环：处理多轮工具调用
            while True:
                # print("Agent 思考中...") # 减少啰嗦的输出
                try:
                    response = await llm_with_tools.ainvoke(messages)
                    
                    # 将 AI 的回答加入历史（包括 tool_calls）
                    # 注意：如果是中间步骤，这个 response 包含 tool_calls；如果是最终步骤，它包含最终文本
                    messages.append(response)
                    
                    if response.tool_calls:
                        if response.content and VERBOSE:
                            logger.debug(f"思考过程: {response.content}")
                            print(f"\n> 思考过程:\n{response.content}\n")

                        # 执行工具
                        for tool_call in response.tool_calls:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]
                            tool_id = tool_call["id"]
                            
                            if VERBOSE:
                                logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")
                                print(f"🔧 调用工具: {tool_name}")
                                print(f"   参数: {tool_args}")
                            
                            selected_tool = next((t for t in tools if t.name == tool_name), None)
                            if selected_tool:
                                try:
                                    use_cache = False
                                    cache_key = None
                                    if tool_name == "query" and isinstance(tool_args, dict) and "sql" in tool_args:
                                        cache_key = tool_args["sql"].strip()
                                        cached = sql_cache.get(cache_key)
                                        if cached is not None:
                                            tool_result = cached
                                            use_cache = True
                                        else:
                                            tool_result = await selected_tool.ainvoke(tool_args)
                                            sql_cache.put(cache_key, tool_result)
                                    elif tool_name == "describe_table" and isinstance(tool_args, dict) and "table" in tool_args:
                                        cache_key = f"desc::{tool_args['table']}"
                                        cached = schema_cache.get(cache_key)
                                        if cached is not None:
                                            tool_result = cached
                                            use_cache = True
                                        else:
                                            tool_result = await selected_tool.ainvoke(tool_args)
                                            schema_cache.put(cache_key, tool_result)
                                    else:
                                        tool_result = await selected_tool.ainvoke(tool_args)
                                except Exception as e:
                                    logger.error(f"工具执行错误: {e}")
                                    tool_result = f"Error: {e}"
                                
                                result_str = str(tool_result)
                                display_result = result_str[:200] + "..." if len(result_str) > 200 else result_str
                                if VERBOSE:
                                    logger.info(f"工具执行结果: {display_result}")
                                    print(f"   结果: {display_result}{' (cached)' if 'use_cache' in locals() and use_cache else ''}\n")
                                
                                # 添加工具结果消息到 messages (用于下一轮思考)
                                tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                                messages.append(tool_msg)
                        
                        # 继续内部循环，让 LLM 再次思考
                        continue
                    
                    else:
                        logger.info(f"Final Answer: {response.content}")
                        print("-" * 50)
                        print(f"Final Answer:\n{response.content}")
                        print("-" * 50)
                        
                        # 将最终回答加入历史
                        # 需要把 messages 中除了动态 system prompt 的部分都加入 chat_history
                        for msg in messages:
                            if not isinstance(msg, SystemMessage):
                                if msg not in chat_history:
                                    chat_history.append(msg)
                        
                        # 确保最终的 AI 回答也在历史中
                        if response not in chat_history:
                            chat_history.append(response)
                        
                        # 从最新的对话中提取 key_info
                        extracted_key_info = extract_key_info_from_messages(chat_history)
                        if extracted_key_info:
                            key_info.update(extracted_key_info)
                        
                        # 自动保存会话
                        save_session(session_id, chat_history, key_info)
                        logger.debug(f"会话已自动保存: {session_id}")
                        break

                except Exception as e:
                    logger.error(f"对话处理出错: {e}")
                    print(f"对话处理出错: {e}")
                    break

    except Exception as e:
        logger.error(f"运行出错: {e}")
        print(f"运行出错: {e}")
    
    # 注意: langchain-mcp-adapters 目前版本不需要显式关闭 client
    # 进程结束时会自动清理子进程

if __name__ == "__main__":
    asyncio.run(main())
