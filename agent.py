import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

# 加载 .env 文件中的环境变量
load_dotenv()

@tool
def search_local_knowledge(query: str) -> str:
    """
    Search for answers in local text files within the 'QA_txt' directory.
    Useful for answering general questions about product features, common issues, and opening requirements.
    The tool searches for keywords in '开场了解需求话术_QA.txt', '产品功能介绍话术_QA.txt', and '常见问题话术_QA.txt'.
    
    Args:
        query: The search query string.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    qa_dir = os.path.join(base_dir, "QA_txt")
    
    if not os.path.exists(qa_dir):
        return f"Error: Directory {qa_dir} does not exist."
    
    results = []
    files_to_search = [
        "开场了解需求话术_QA.txt", 
        "产品功能介绍话术_QA.txt", 
        "常见问题话术_QA.txt"
    ]
    
    for filename in files_to_search:
        filepath = os.path.join(qa_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # 简单的全文搜索
                    if query in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if query in line:
                                context_start = max(0, i - 2)
                                context_end = min(len(lines), i + 5)
                                snippet = "\n".join(lines[context_start:context_end])
                                results.append(f"--- Found in {filename} ---\n{snippet}\n")
                    else:
                        # 尝试更宽松的搜索：如果 query 是问句，尝试提取关键词
                        # 这里简单处理，如果完全没找到，就不返回
                        pass
                        
            except Exception as e:
                results.append(f"Error reading {filename}: {str(e)}")
    
    if not results:
        return "No direct matches found in local knowledge base."
        
    return "\n".join(results)

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
    
    # 真实地等待用户（主管）输入
    approval = input("主管请批复 (同意/拒绝/其他指令): ")
    return f"主管批复: {approval}"

async def main():
    # 1. 定义大模型 (LLM)
    print("初始化 LLM...")
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
    
    mysql_env = os.environ.copy() # 继承当前环境变量
    if os.path.exists(mysql_env_path):
        print(f"读取 MySQL 环境变量: {mysql_env_path}")
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
    
    print(f"MCP Server 脚本路径: {script_path}")
    
    # 3. 初始化 MCP Client
    client = MultiServerMCPClient({
        "mysql": {
            "command": "node",
            "args": [script_path],
            "transport": "stdio",
            "env": mysql_env
        }
    })
        
    print("连接 MCP Server 并获取工具...")
    try:
        mcp_tools = await client.get_tools()
        # 合并 MCP 工具和本地工具
        tools = mcp_tools + [search_local_knowledge, ask_supervisor_approval]
        
        print(f"成功获取 {len(tools)} 个工具: {[t.name for t in tools]}")

        # 4. 手动实现简单的 Agent Loop
        print("开始运行智能体... (输入 'exit' 或 'quit' 退出)")
        
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
                if user_input.lower() in ["exit", "quit"]:
                    break
            except EOFError:
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
                        # 打印思考过程（如果有）
                        if response.content:
                            print(f"\n> 思考过程:\n{response.content}\n")

                        # 执行工具
                        for tool_call in response.tool_calls:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]
                            tool_id = tool_call["id"]
                            
                            # 模拟 UI 卡片展示
                            print(f"🔧 调用工具: {tool_name}")
                            print(f"   参数: {tool_args}")
                            
                            # 找到对应的工具函数
                            selected_tool = next((t for t in tools if t.name == tool_name), None)
                            if selected_tool:
                                try:
                                    # 工具可能是同步或异步的
                                    tool_result = await selected_tool.ainvoke(tool_args)
                                except Exception as e:
                                    tool_result = f"Error: {e}"
                                
                                # 截断过长的输出，保持界面整洁
                                result_str = str(tool_result)
                                display_result = result_str[:200] + "..." if len(result_str) > 200 else result_str
                                print(f"   结果: {display_result}\n")
                                
                                # 添加工具结果消息到 messages (用于下一轮思考)
                                tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                                messages.append(tool_msg)
                        
                        # 继续内部循环，让 LLM 再次思考
                        continue
                    
                    else:
                        # 没有工具调用，说明是最终回答
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
                    print(f"对话处理出错: {e}")
                    break

    except Exception as e:
        print(f"运行出错: {e}")
    
    # 注意: langchain-mcp-adapters 目前版本不需要显式关闭 client
    # 进程结束时会自动清理子进程

if __name__ == "__main__":
    asyncio.run(main())
