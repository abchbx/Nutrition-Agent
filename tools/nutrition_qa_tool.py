from typing import Dict, Any, Type
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
# 推荐更新：从 langchain_openai 导入
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from config import AGENT_MODEL, AGENT_TEMPERATURE, EMBEDDING_MODEL 
from pydantic import BaseModel, Field
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_MODEL, AGENT_TEMPERATURE

class NutritionQAInput(BaseModel):
    """营养学问答工具输入模型"""
    question: str = Field(description="营养学相关问题")
    detail_level: str = Field(default="中等", description="回答详细程度：简单、中等、详细")

class NutritionQATool(BaseTool):
    """营养学知识问答工具"""
    name: str = "nutrition_qa"
    description: str = "回答营养学相关的知识问题，包括营养原理、健康饮食、营养素功能等"
    args_schema: Type[BaseModel] = NutritionQAInput
    
    # --- 修复1：声明所有实例属性并提供默认值 ---
    llm: Any = None
    embeddings: Any = None
    knowledge_base: Any = None
    qa_prompt: Any = None
    qa_chain: Any = None
    
    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE
        )
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.knowledge_base = self._create_knowledge_base()

        self.qa_prompt = PromptTemplate(
            input_variables=["question", "context", "detail_level"],
            template="""
你是一位专业的营养学专家，请根据提供的上下文信息回答用户的问题。

用户问题：{question}

相关营养学知识：
{context}

回答详细程度要求：{detail_level}

请基于以上信息，提供专业、准确、易懂的回答。如果上下文信息不足以完全回答问题，请结合你的专业知识进行补充。

回答要求：
1. 科学准确，基于营养学原理
2. 实用性强，能指导实际生活
3. 语言通俗易懂，避免过多专业术语
4. 根据详细程度要求调整回答深度
5. 如有必要，提供具体的数据和例子

---
**格式要求：**
请使用Markdown格式进行排版，以提高可读性。可以使用标题（如 '##'）、要点（如 '*' 或 '-'）和粗体（如 '**重点**'）来组织你的回答。
"""
        )
        # --- 修复2：使用新的LCEL语法 (prompt | llm) ---
        self.qa_chain = self.qa_prompt | self.llm

    def _create_knowledge_base(self) -> FAISS:
        nutrition_docs = [
            Document(page_content="宏量营养素包括...", metadata={"category": "宏量营养素", "topic": "碳水化合物"}),
            Document(page_content="蛋白质是生命的基础...", metadata={"category": "宏量营养素", "topic": "蛋白质"}),
            Document(page_content="脂肪是重要的能量储存形式...", metadata={"category": "宏量营养素", "topic": "脂肪"}),
            Document(page_content="微量营养素包括...", metadata={"category": "微量营养素", "topic": "维生素和矿物质"}),
            Document(page_content="膳食纤维是不能被...", metadata={"category": "其他营养素", "topic": "膳食纤维"}),
            Document(page_content="水是生命必需的营养素...", metadata={"category": "其他营养素", "topic": "水"}),
            Document(page_content="健康饮食的基本原则...", metadata={"category": "健康饮食", "topic": "基本原则"}),
            Document(page_content="体重管理的基本原理...", metadata={"category": "体重管理", "topic": "热量平衡"}),
            Document(page_content="不同生命阶段...", metadata={"category": "特殊人群", "topic": "生命阶段营养"}),
            Document(page_content="运动营养需要根据...", metadata={"category": "运动营养", "topic": "运动与营养"})
        ]

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(nutrition_docs)

        return FAISS.from_documents(texts, self.embeddings)

    def _run(self, question: str, detail_level: str = "中等") -> str:
        try:
            relevant_docs = self.knowledge_base.similarity_search(question, k=3)
            context = "\n\n".join(doc.page_content for doc in relevant_docs)
            if not context:
                context = "未找到相关的营养学知识文档，将基于专业知识回答。"

            # --- 修复2：使用 .invoke() 代替 .run()，并传入字典 ---
            # .invoke() 的返回值直接就是一个内容对象，我们需要提取其 .content 属性
            response = self.qa_chain.invoke({
                "question": question,
                "context": context,
                "detail_level": detail_level
            })
            answer = response.content

            result = f"📚 营养学知识问答：\n"
            result += f"❓ 问题：{question}\n"
            result += f"📝 详细程度：{detail_level}\n\n"
            result += "💡 回答：\n"
            result += "=" * 50 + "\n"
            result += answer

            if relevant_docs:
                result += "\n\n" + "=" * 50 + "\n"
                result += "📖 参考来源：\n"
                for i, doc in enumerate(relevant_docs, 1):
                    result += f"{i}. {doc.metadata.get('category', '营养学')} - {doc.metadata.get('topic', '相关知识')}\n"
            return result
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

    # --- 修复1：声明所有实例属性并提供默认值 ---
    llm: Any = None
    myth_prompt: Any = None
    myth_chain: Any = None

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(
            model_name=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE
        )

        self.myth_prompt = PromptTemplate(
            input_variables=["myth"],
            template="""
你是一位专业的营养学专家，你的任务是辨析以下营养误区或流行说法。

**误区/说法：** {myth}

---
请使用清晰的Markdown格式，并严格按照以下结构进行分析，每个部分使用二级标题（##）：

## 📖 说法的来源与流行程度
* 在这里分析这个说法的起源，以及它为什么会流行起来。

## 🔬 科学事实与依据
* 请从科学角度出发，列出与此说法相关的核心事实和研究证据。
* 可以使用要点来罗列，并将 **关键词** 加粗。

## ✅ 正确性与局限性
* 分析这个说法在多大程度上是正确的，以及它的适用范围和局限性。
* 例如：它是否只在特定情况下成立？

## ⚠️ 可能的危害或风险
* 如果人们盲目相信并遵循这个说法，可能会带来哪些健康风险或负面影响？

## 👍 科学的建议与替代方案
* 针对这个误区，提供科学、可行的饮食或生活方式建议。
* 如果原说法有可取之处，可以提出更科学的替代方案。
"""
        )
        # --- 修复2：使用新的LCEL语法 (prompt | llm) ---
        self.myth_chain = self.myth_prompt | self.llm

    def _run(self, myth: str) -> str:
        try:
            # --- 修复2：使用 .invoke() 代替 .run()，并传入字典 ---
            response = self.myth_chain.invoke({"myth": myth})
            analysis = response.content
            
            result = f"🔍 营养误区辨析：\n"
            result += f"🤔 误区：{myth}\n\n"
            result += "📋 科学分析：\n"
            result += "=" * 50 + "\n"
            result += analysis
            return result
        except Exception as e:
            return f"辨析营养误区时发生错误: {str(e)}"