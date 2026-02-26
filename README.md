# 电商售前智能助手 (E-commerce Sales Agent)

这是一个基于 LangChain + DeepSeek + MCP + RAG 构建的电商售前智能助手。它能够扮演专业的售前客服，引导用户完成产品咨询、选型、报价及议价流程，并支持数据库实时查询和人机协同（主管审批）。

## 🚀 功能特性

*   **引导式问答**：遵循严格的销售话术流程（了解场景 -> 推荐 -> 报价）。
*   **数据库集成 (MCP)**：通过 MCP 协议连接本地 MySQL 数据库，实时查询最新的产品价格、配置和库存。
*   **知识库增强 (RAG)**：基于 ChromaDB 的语义检索，精准回答关于质保、发票、物流等非结构化问题。
*   **人机协同**：遇到用户过度砍价时，Agent 会自动触发“向主管申请”流程，由人工介入审批。
*   **多轮对话记忆**：支持上下文理解，能够记住用户的需求变更。

## 🛠️ 环境准备

### 1. 基础环境
*   Python 3.10+
*   Node.js (用于运行 MCP MySQL Server)
*   MySQL 数据库

### 2. 安装依赖
```bash
pip install -r requirements.txt
```
同时进入 `mcp-mysql-server` 目录安装 Node 依赖：
```bash
cd mcp-mysql-server
npm install
```

### 3. 配置环境变量
在项目根目录创建 `.env` 文件：
```env
DEEPSEEK_API_KEY=sk-your-key-here
```
配置数据库连接（修改 `mcp-mysql-server/env`）：
```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=good_message_qa
```

## 🏗️ 构建知识库

在首次运行前，需要将本地的话术文档（TXT）向量化存入数据库：

1.  确保 `QA_txt` 目录下有你的问答文档（如 `常见问题话术_QA.txt`）。
2.  运行构建脚本：
    ```bash
    python build_rag.py
    ```
    > 这一步会自动下载 Embedding 模型并创建本地 ChromaDB 索引。

## 🏃‍♂️ 运行项目

启动智能助手：
```bash
python agent.py
```

## 🎮 使用指南

### 基础对话
直接在终端输入你的问题，例如：
*   “你好，我想买台一体机”
*   “开会用的，经常远程”
*   “要55寸的，开发票”

### 触发议价流程
如果你尝试大幅砍价（低于底价），Agent 会进入申请模式：
1.  **用户**：“太贵了，3000块卖不卖？”
2.  **Agent**：“好的，我帮您申请一下，您稍等。”
3.  **终端（主管视角）**：会弹出申请单，等待你输入指令。
    ```text
    📢 【向主管申请价格】
    **申请价格**
    ...
    主管请批复 (同意/拒绝/其他指令): 
    ```
4.  **主管**：输入 `同意` 或 `拒绝`。
5.  **Agent**：根据你的指令回复用户。

## 📂 项目结构

*   `agent.py`: 主程序，负责 Agent 核心循环和模型交互。
*   `tools.py`: 工具集（RAG 检索、主管审批）。
*   `build_rag.py`: 知识库构建脚本。
*   `system_prompt.txt`: Agent 的人设和业务规则。
*   `mcp-mysql-server/`: MySQL MCP 服务端代码。
*   `QA_txt/`: 原始问答语料。
*   `chromadb/`: 向量数据库存储目录。
