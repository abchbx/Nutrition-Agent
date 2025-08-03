import pandas as pd
import numpy as np
# faiss-cpu 或者 faiss-gpu 取决于您的安装
# import faiss 
import json
import os
from typing import List, Dict, Any, Optional
# --- 修改开始 ---
# 1. 导入我们需要的本地模型类和配置
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL
# --- 修改结束 ---
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
import pickle

class NutritionDatabase:
    """营养成分数据库管理类"""

    def __init__(self, data_path: str = "./data/nutrition_data.csv", 
                 vector_db_path: str = "./data/faiss_index"):
        """
        初始化营养数据库
        
        Args:
            data_path: 营养数据CSV文件路径
            vector_db_path: 向量数据库存储路径
        """
        self.data_path = data_path
        self.vector_db_path = vector_db_path
        self.nutrition_data = None
        self.vector_store = None
        
        # --- 修改开始 ---
        # 2. 使用我们统一配置的本地模型
        #    如果您的电脑有NVIDIA显卡，可以使用下面这行来加速
        #    self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, model_kwargs={'device': 'cuda'})
        #    如果使用CPU，用下面这行
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        # --- 修改结束 ---


        # 创建数据目录
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        os.makedirs(vector_db_path, exist_ok=True)

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载营养数据"""
        try:
            if os.path.exists(self.data_path):
                self.nutrition_data = pd.read_csv(self.data_path)
                print(f"✅ 成功加载营养数据: {len(self.nutrition_data)} 条记录")
            else:
                print("📝 营养数据文件不存在，创建示例数据...")
                self._create_sample_data()

            # 加载或创建向量数据库
            self._load_or_create_vector_db()

        except Exception as e:
            print(f"❌ 加载营养数据失败: {e}")
            # 如果加载失败，可能是因为数据文件有问题，尝试用示例数据重建
            print("尝试使用示例数据重新创建数据库...")
            self._create_sample_data()
            self._create_vector_db()

    def _create_sample_data(self):
        """创建示例营养数据"""
        sample_data = {
            "food_name": [
                "苹果", "香蕉", "橙子", "草莓", "葡萄",
                "鸡胸肉", "牛肉", "鱼肉", "鸡蛋", "牛奶",
                "大米", "全麦面包", "燕麦", "红薯", "西兰花",
                "胡萝卜", "菠菜", "西红柿", "黄瓜", "豆腐"
            ],
            "calories": [52, 89, 47, 32, 69, 165, 250, 206, 155, 42, 
                         130, 247, 68, 86, 34, 41, 23, 18, 16, 76],
            "protein": [0.3, 1.1, 0.9, 0.7, 0.7, 31, 26, 22, 13, 3.4,
                        2.7, 13, 2.4, 1.6, 2.8, 0.9, 2.9, 0.9, 0.7, 8],
            "carbs": [14, 23, 12, 8, 18, 0, 0, 0, 1.1, 5,
                      28, 41, 12, 20, 7, 10, 3.6, 3.9, 3.6, 1.9],
            "fat": [0.2, 0.3, 0.1, 0.3, 0.2, 3.6, 15, 12, 11, 1,
                    0.3, 3.4, 1.4, 0.1, 0.4, 0.2, 0.4, 0.2, 0.1, 4.8],
            "fiber": [2.4, 2.6, 2.4, 2, 0.9, 0, 0, 0, 0, 0,
                      0.4, 7, 4, 3, 2.6, 2.8, 2.2, 1.2, 0.5, 0.3],
            "vitamin_c": [4.6, 8.7, 53.2, 58.8, 3.2, 0, 0, 0, 0, 0,
                          0, 0, 0, 2.4, 89.2, 5.9, 28.1, 13.7, 2.8, 0],
            "calcium": [6, 5, 40, 16, 10, 15, 18, 25, 56, 113,
                        28, 54, 52, 30, 47, 33, 99, 10, 16, 350],
            "iron": [0.1, 0.3, 0.1, 0.4, 0.4, 1.0, 2.6, 0.8, 1.8, 0.03,
                     0.8, 3.6, 1.3, 0.6, 0.7, 0.3, 2.7, 0.3, 0.3, 5.4],
            "category": ["水果", "水果", "水果", "水果", "水果",
                         "肉类", "肉类", "肉类", "蛋类", "乳制品",
                         "谷物", "谷物", "谷物", "蔬菜", "蔬菜",
                         "蔬菜", "蔬菜", "蔬菜", "蔬菜", "豆制品"]
        }

        self.nutrition_data = pd.DataFrame(sample_data)
        self.nutrition_data.to_csv(self.data_path, index=False, encoding='utf-8-sig')
        print(f"✅ 创建示例营养数据: {len(self.nutrition_data)} 条记录")

    def _load_or_create_vector_db(self):
        """加载或创建向量数据库"""
        # 为了与新版faiss-cpu兼容，直接使用FAISS类的save_local和load_local方法
        if os.path.exists(self.vector_db_path) and os.path.exists(os.path.join(self.vector_db_path, "index.faiss")):
            try:
                self.vector_store = FAISS.load_local(self.vector_db_path, self.embeddings, allow_dangerous_deserialization=True)
                print("✅ 成功加载向量数据库")
            except Exception as e:
                print(f"❌ 加载向量数据库失败: {e}")
                self._create_vector_db()
        else:
            self._create_vector_db()

    def _create_vector_db(self):
        """创建向量数据库"""
        print("⏳ 正在创建向量数据库...")
        documents = []

        for _, row in self.nutrition_data.iterrows():
            description = (f"{row['food_name']}是一种{row['category']}，每100g含有"
                           f"热量{row['calories']}千卡，蛋白质{row['protein']}g，"
                           f"碳水化合物{row['carbs']}g，脂肪{row['fat']}g，"
                           f"膳食纤维{row['fiber']}g，维生素C{row['vitamin_c']}mg，"
                           f"钙{row['calcium']}mg，铁{row['iron']}mg。")

            doc = Document(
                page_content=description,
                metadata=row.to_dict() # 将整行数据作为元数据
            )
            documents.append(doc)

        # 创建向量数据库
        self.vector_store = FAISS.from_documents(documents, self.embeddings)

        # 保存向量数据库
        self.vector_store.save_local(self.vector_db_path)
        print("✅ 成功创建并保存向量数据库")

    def search_nutrition(self, food_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索食物营养信息
        """
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.similarity_search(food_name, k=top_k)
            # 直接返回元数据列表，因为元数据就是完整的营养信息
            return [doc.metadata for doc in results]

        except Exception as e:
            print(f"❌ 搜索营养信息失败: {e}")
            return []

    # ... get_nutrition_by_name, get_foods_by_category, get_all_categories 等方法保持不变 ...
    def get_nutrition_by_name(self, food_name: str) -> Optional[Dict[str, Any]]:
        if self.nutrition_data is None:
            return None
        result = self.nutrition_data[self.nutrition_data['food_name'] == food_name]
        if len(result) > 0:
            return result.iloc[0].to_dict()
        return None

    def get_foods_by_category(self, category: str) -> List[Dict[str, Any]]:
        if self.nutrition_data is None:
            return []
        results = self.nutrition_data[self.nutrition_data['category'] == category]
        return results.to_dict('records')

    def get_all_categories(self) -> List[str]:
        if self.nutrition_data is None:
            return []
        return self.nutrition_data['category'].unique().tolist()