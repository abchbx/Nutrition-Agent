# 🍎 营养师 Agent (Nutrition-Agent)

Nutrition-Agent 是一个基于大型语言模型（LLM）的智能营养师助手。它能够根据您的个人身体数据和健康目标，提供个性化的饮食建议、回答营养学问题，并帮助您规划健康的饮食方案。

[](https://www.google.com/search?q=https://your-streamlit-app-url.com)  \#\# ✨ 主要功能

  * **个性化用户档案**：为每位用户创建并管理独立的健康档案，包含年龄、身高、体重、健康目标、饮食偏好等信息。
  * **食物营养查询**：快速查询各种食物的详细营养成分，包括热量、蛋白质、维生素等。
  * **智能饮食建议**：根据用户的个人档案和具体目标（如减肥、增肌、改善健康），生成科学、可行的饮食方案。
  * **膳食计划生成**：为特定餐食（早餐、午餐、晚餐）或加餐提供具体的食物搭配建议。
  * **营养知识问答**：回答专业的营养学问题，例如各种营养素的功能、健康饮食原则等。
  * **营养误区辨析**：针对常见的“伪科学”和流行说法，提供科学的分析和澄清。
  * **对话式交互**：拥有对话记忆功能，能够理解上下文，提供连贯、流畅的交互体验。

## 🛠️ 技术栈

  * **核心框架**：LangChain
  * **前端界面**：Streamlit
  * **语言模型 (LLM)**：支持 ZhipuAI/GLM-4.5, glm-4-flash 等模型
  * **向量数据库**：FAISS (Facebook AI Similarity Search)
  * **词向量模型**：BAAI/bge-large-zh-v1.5 (用于文本向量化)
  * **数据处理**：Pandas, NumPy

## 📂 项目结构

```
Nutrition-Agent/
├── data/
│   ├── nutrition_data.csv         # 营养成分数据
│   └── faiss_index/               # FAISS 向量索引
├── tools/
│   ├── diet_advice_tool.py        # 饮食建议工具
│   ├── nutrition_qa_tool.py       # 营养问答工具
│   └── nutrition_query_tool.py    # 食物查询工具
├── user_profiles/
│   └── user_xxx.json              # 用户个人档案
├── .env                           # 环境变量配置
├── app.py                         # Streamlit 前端应用
├── config.py                      # 项目配置加载
├── nutrition_agent.py             # Agent 核心逻辑
├── nutrition_database.py          # 营养数据库管理
├── requirements.txt               # Python 依赖包
└── README.md                      # 项目说明文档
```

## 🚀 快速开始

### 1\. 环境准备

  * 确保您已安装 Python 3.9 或更高版本。
  * (推荐) 创建并激活一个虚拟环境：
    ```bash
    python -m venv venv
    source venv/bin/activate  # on Windows, use `venv\Scripts\activate`
    ```

### 2\. 克隆项目

```bash
git clone https://github.com/your-username/Nutrition-Agent.git
cd Nutrition-Agent
```

### 3\. 安装依赖

```bash
pip install -r requirements.txt
```

### 4\. 配置环境变量

项目需要一个 `.env` 文件来管理 API 密钥和关键配置。

1.  复制 `.env.example` (如果提供) 或手动创建一个名为 `.env` 的文件。

2.  编辑 `.env` 文件，填入您的 API 密钥和基础 URL。

    ```dotenv
    # OpenAI 或兼容的 API 配置
    OPENAI_API_KEY="sk-your_api_key_here"
    OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1" # 根据您的服务商修改

    # Agent 模型配置
    AGENT_MODEL=ZhipuAI/GLM-4.5
    # ... 其他配置保持默认即可
    ```

    > **注意**: `OPENAI_BASE_URL` 需要指向您使用的语言模型服务商的 API 端点。

### 5\. 运行应用

一切准备就绪后，使用以下命令启动 Streamlit 应用：

```bash
streamlit run app.py
```

应用启动后，浏览器将自动打开一个新标签页，您就可以开始与您的专属营养师 Agent 互动了！

## 💡 工作流简介

1.  **用户交互**：用户在 Streamlit 构建的前端界面输入问题或更新个人档案。
2.  **Agent 接收**：`nutrition_agent.py` 中的 `NutritionAgent` 接收到请求，并加载用户的历史对话和档案信息。
3.  **意图判断与工具选择**：Agent (LLM) 分析用户的输入，判断其意图，并决定调用哪个或哪些工具（如查询食物、生成建议等）。
4.  **工具执行**：被选中的工具（例如 `NutritionQueryTool`）会执行具体任务，可能会与 FAISS 向量数据库或用户档案进行交互。
5.  **结果整合与生成回复**：Agent (LLM) 将工具返回的结果整合起来，并结合对话上下文，生成一段自然、流畅的回复。
6.  **展示给用户**：最终的回复通过 Streamlit 界面展示给用户，并保存到对话历史中。

## 📜 许可证

本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源。
