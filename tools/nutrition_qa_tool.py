# 添加项目根目录到路径
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Type

import numpy as np
from faiss import IndexFlatL2
from langchain_community.docstore import InMemoryDocstore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from config import AGENT_MODEL, AGENT_TEMPERATURE

# Setup logger for nutrition_qa_tool.py
from config import agent_logger as logger  # Re-use agent logger or create a new one if needed


class NutritionQAInput(BaseModel):
    """营养学问答工具输入模型"""

    question: str = Field(description="营养学相关问题")
    detail_level: str = Field(default="中等", description="回答详细程度：简单、中等、详细")


class NutritionQATool(BaseTool):
    """营养学知识问答工具"""

    name: str = "nutrition_qa"
    description: str = "回答营养学相关的知识问题，包括营养原理、健康饮食、营养素功能等"
    args_schema: Type[BaseModel] = NutritionQAInput

    llm: Any = None
    embeddings: Any = None
    knowledge_base: Any = None
    qa_prompt: Any = None
    qa_chain: Any = None

    def __init__(self, embeddings: HuggingFaceEmbeddings):
        super().__init__()
        self.llm = ChatOpenAI(model_name=AGENT_MODEL, temperature=AGENT_TEMPERATURE)
        self.embeddings = embeddings
        self.knowledge_base = self._create_knowledge_base()

        self.qa_prompt = PromptTemplate(
            input_variables=["question", "context", "detail_level"],
            template="""
你是一位经验丰富的注册营养师 (RDN)，名叫"小营"。请根据提供的上下文信息和你的专业知识，结构化地回答用户的问题。

**用户问题:** {question}

**相关营养学知识:**
{context}

**回答详细程度要求:** {detail_level}

---
**## 输出格式要求**
请严格按照以下 Markdown 格式组织你的回答，确保内容层次分明，并且可以直接被主 Agent 用作 `nutrition_qa` 模板的内容：

#### 🎯 核心答案
* (用一两句话直接回答问题的核心)

#### 🔬 详细解释
* (根据详细程度要求，展开解释背后的科学原理和逻辑)
* (可以列出多个要点，并对 **关键词** 进行加粗)

#### 👍 实践建议
* (提供2-3条具体、可操作的生活或饮食建议)

请确保回答科学准确、语言通俗易懂。
合理使用表情符号和格式化来增强可读性。
重要信息要突出显示，复杂概念要用简单语言解释。
""",
        )
        self.qa_chain = self.qa_prompt | self.llm

    def _create_knowledge_base(self) -> FAISS:
        # 尝试从外部 Markdown 文件加载知识库
        knowledge_base_path = "knowledge_base.md"
        nutrition_docs = []

        if os.path.exists(knowledge_base_path):
            try:
                with open(knowledge_base_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 简单地将整个文件内容作为一个文档处理，或可以按章节分割
                # 这里我们按 '####' 标题分割成多个文档
                sections = content.split("\n#### ")
                for i, section in enumerate(sections):
                    if section.strip():
                        # 重新加上标题前缀
                        page_content = section if i == 0 else "#### " + section
                        nutrition_docs.append(
                            Document(
                                page_content=page_content.strip(),
                                metadata={"source": "knowledge_base.md", "section_id": i},
                            )
                        )
                print(f"✅ 从 {knowledge_base_path} 加载了 {len(nutrition_docs)} 个知识片段。")
            except Exception as e:
                print(f"⚠️ 从 {knowledge_base_path} 加载知识库时出错: {e}")
        else:
            print(f"⚠️ 知识库文件 {knowledge_base_path} 未找到，使用内置默认知识。")

        # 如果没有从文件加载到内容，则使用默认的硬编码知识
        if not nutrition_docs:
            nutrition_docs = [
                Document(
                    page_content="宏量营养素包括碳水化合物、蛋白质和脂肪，是身体能量的主要来源。",
                    metadata={"category": "宏量营养素", "topic": "基础"},
                ),
                Document(
                    page_content="蛋白质是构成肌肉、器官和酶的基础，对于生长和修复至关重要。",
                    metadata={"category": "宏量营养素", "topic": "蛋白质"},
                ),
                Document(
                    page_content="膳食纤维有助于肠道健康，能增加饱腹感，常见于蔬菜、水果和全谷物中。",
                    metadata={"category": "其他营养素", "topic": "膳食纤维"},
                ),
            ]

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(nutrition_docs)

        try:
            print("💡 正在为QA工具创建知识库 (使用 IndexFlatL2)...")

            embeddings_vectors = self.embeddings.embed_documents([doc.page_content for doc in texts])

            # 检查是否有嵌入向量生成
            if not embeddings_vectors:
                print("⚠️ 未能生成嵌入向量，使用 FAISS 的 from_documents 方法创建知识库")
                return FAISS.from_documents(texts, self.embeddings)

            vectors = np.array(embeddings_vectors, dtype=np.float32)

            # 检查向量维度
            if vectors.size == 0 or len(vectors.shape) < 2:
                print("⚠️ 嵌入向量维度不正确，使用 FAISS 的 from_documents 方法创建知识库")
                return FAISS.from_documents(texts, self.embeddings)

            embedding_dimension = vectors.shape[1]

            index = IndexFlatL2(embedding_dimension)
            index.add(vectors)

            docstore = InMemoryDocstore({str(i): doc for i, doc in enumerate(texts)})
            index_to_docstore_id = {i: str(i) for i in range(len(texts))}

            knowledge_base = FAISS(
                embedding_function=self.embeddings.embed_query,
                index=index,
                docstore=docstore,
                index_to_docstore_id=index_to_docstore_id,
            )

            print("✅ QA工具知识库创建成功!")
            return knowledge_base

        except Exception as e:
            print(f"❌ 创建QA知识库时出错: {e}")
            return FAISS.from_documents(texts, self.embeddings)

    def _run(self, question: str, detail_level: str = "中等") -> str:
        try:
            relevant_docs = self.knowledge_base.similarity_search(question, k=3)
            context = "\n\n".join(doc.page_content for doc in relevant_docs)
            if not context:
                context = "未找到相关的营养学知识文档，将基于专业知识回答。"

            response = self.qa_chain.invoke({"question": question, "context": context, "detail_level": detail_level})
            return response.content
        except Exception as e:
            return f"回答营养学问题时发生错误: {str(e)}"


class NutritionMythInput(BaseModel):
    """营养误区辨析工具输入模型"""

    myth: str = Field(description="需要辨析的营养误区或流行说法")


class NutritionMythTool(BaseTool):
    """营养误区辨析工具"""

    name: str = "nutrition_myth"
    description: str = "辨析营养学误区和流行说法，提供科学依据"
    args_schema: Type[BaseModel] = NutritionMythInput

    llm: Any = None
    myth_prompt: Any = None
    myth_chain: Any = None

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(model_name=AGENT_MODEL, temperature=AGENT_TEMPERATURE)

        self.myth_prompt = PromptTemplate(
            input_variables=["myth"],
            template="""
你是一位经验丰富的注册营养师 (RDN)，名叫"小营"。你的任务是科学地辨析以下营养误区或流行说法。

**## 🧐 待辨析说法**
{myth}

---
**## 输出格式要求**
请使用清晰的 Markdown 格式，并严格按照以下结构进行分析，每个部分使用二级标题。这部分的输出可以直接被主 Agent 用作 `nutrition_qa` 模板的内容：

#### 🎯 核心答案
* (直接点明该说法是正确、错误还是有局限性)

#### 🔬 详细解释
* (从科学角度出发，列出与此说法相关的核心事实和研究证据，并将 **关键词** 加粗)
* (分析该说法可能的起源和流行的原因)

#### 👍 实践建议
* (针对这个误区，提供科学、可行的饮食或生活方式建议)
* (如果该说法有部分正确性，说明在什么情况下适用)

请确保回答科学准确、语言通俗易懂。
合理使用表情符号和格式化来增强可读性。
重要信息要突出显示，复杂概念要用简单语言解释。
""",
        )
        self.myth_chain = self.myth_prompt | self.llm

    def _run(self, myth: str) -> str:
        try:
            response = self.myth_chain.invoke({"myth": myth})
            return response.content
        except Exception as e:
            return f"辨析营养误区时发生错误: {str(e)}"
