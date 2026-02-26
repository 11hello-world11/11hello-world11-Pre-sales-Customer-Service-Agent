from typing import List
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from tools import search_local_knowledge, ask_supervisor_approval
from logger import logger

load_dotenv()

async def main():
    logger.info("初始化 LLM...")
    llm = ChatOpenAI(
        model="deepseek-chat", 
        temperature=0,
        base_url="https://api.deepseek.com",
        api_key=os.environ.get("DEEPSEEK_API_KEY")
    )

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
        tools = mcp_tools + [search_local_knowledge, ask_supervisor_approval]
        
        logger.info(f"成功获取 {len(tools)} 个工具: {[t.name for t in tools]}")
        logger.info("开始运行智能体... (输入 'exit' 或 'quit' 退出)")
        
        # 读取 System Prompt
        system_prompt_path = os.path.join(base_dir, "system_prompt.txt")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompt_content = f.read()
        else:
            system_prompt_content = "你是一个智能数据库助手。" # 默认 Prompt

        system_prompt = SystemMessage(content=system_prompt_content)
        chat_history = [system_prompt]
        llm_with_tools = llm.bind_tools(tools)

        while True:
            try:
                user_input = input("\nUser: ")
                logger.info(f"用户输入: {user_input}")
                if user_input.lower() in ["exit", "quit"]:
                    logger.info("用户退出会话")
                    break
            except EOFError:
                logger.warning("收到 EOF，退出会话")
                break

            # 构造当前对话的消息列表
            # 将用户输入加入历史
            chat_history.append(HumanMessage(content=user_input))
            
            # 这里的 messages 是当前所有上下文
            messages = list(chat_history)
            
            # 内部循环：处理多轮工具调用
            while True:
                # print("Agent 思考中...") # 减少啰嗦的输出
                try:
                    response = await llm_with_tools.ainvoke(messages)
                    
                    # 将 AI 的回答加入历史（包括 tool_calls）
                    # 注意：如果是中间步骤，这个 response 包含 tool_calls；如果是最终步骤，它包含最终文本
                    messages.append(response)
                    
                    if response.tool_calls:
                        if response.content:
                            logger.debug(f"思考过程: {response.content}")
                            print(f"\n> 思考过程:\n{response.content}\n")

                        # 执行工具
                        for tool_call in response.tool_calls:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]
                            tool_id = tool_call["id"]
                            
                            logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")
                            print(f"🔧 调用工具: {tool_name}")
                            print(f"   参数: {tool_args}")
                            
                            selected_tool = next((t for t in tools if t.name == tool_name), None)
                            if selected_tool:
                                try:
                                    tool_result = await selected_tool.ainvoke(tool_args)
                                except Exception as e:
                                    logger.error(f"工具执行错误: {e}")
                                    tool_result = f"Error: {e}"
                                
                                result_str = str(tool_result)
                                display_result = result_str[:200] + "..." if len(result_str) > 200 else result_str
                                logger.info(f"工具执行结果: {display_result}")
                                print(f"   结果: {display_result}\n")
                                
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
                        chat_history.append(response)
                        # 将中间产生的工具交互也合并到 history 中，保持上下文完整
                        # 注意：我们需要找出 messages 中新增的部分（除了最后一条 response）
                        # 简单起见，直接更新 chat_history 为当前的 messages
                        chat_history = list(messages)
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
