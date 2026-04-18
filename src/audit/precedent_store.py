"""
先例数据库模块

版本: v1.0
创建日期: 2026-03-20
Author: Agora Governance Contributors
状态: Phase 2 开发中

功能:
- 先例存储（JSON 文件）
- 先例索引（TF-IDF）
- 先例检索（语义搜索）
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


@dataclass
class Precedent:
    """先例数据结构"""

    decision_id: str                    # 决策 ID
    timestamp: str                       # 时间戳
    task_id: str                         # 任务 ID
    description: str                     # 任务描述
    approved: bool                       # 是否批准
    stage: str                           # 决策阶段
    reasoning: str                       # 决策理由
    local_reviews: dict                  # Local Crits 审查结果
    global_votes: dict | None            # Global Crits 投票结果
    tmind_decision: dict | None          # T-Mind 决策

    # 先例特定字段
    precedent: bool = False              # 是否标记为先例
    precedent_weight: float = 0.0        # 先例权重（0-5）
    citation_count: int = 0              # 引用次数
    tags: List[str] = None               # 标签
    category: str = ""                   # 分类

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class PrecedentDatabase:
    """先例数据库"""

    def __init__(self, db_path: str = "agora/governance/precedents.jsonl"):
        """
        初始化先例数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.precedents: List[Precedent] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None

        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:  # 只有当目录不为空时才创建
            os.makedirs(db_dir, exist_ok=True)

        # 加载现有先例
        self.load()

    def load(self):
        """从文件加载先例"""
        if not os.path.exists(self.db_path):
            return

        with open(self.db_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    precedent = Precedent(**data)
                    self.precedents.append(precedent)

        # 构建索引
        self._build_index()

    def save(self):
        """保存先例到文件"""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            for precedent in self.precedents:
                f.write(json.dumps(asdict(precedent), ensure_ascii=False) + '\n')

    def add(self, precedent: Precedent):
        """
        添加先例

        Args:
            precedent: 先例对象
        """
        self.precedents.append(precedent)
        self._build_index()
        self.save()

    def _build_index(self):
        """构建 TF-IDF 索引"""
        if not self.precedents:
            return

        # 构建文档（reasoning + tags）
        documents = [
            f"{p.reasoning} {' '.join(p.tags)}"
            for p in self.precedents
        ]

        # 创建 TF-IDF 向量器
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            min_df=1,  # 至少出现在 1 个文档中
            max_df=1.0  # 出现在所有文档中（避免单文档时的错误）
        )

        # 构建 TF-IDF 矩阵
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)

    def search(
        self,
        query: str,
        threshold: float = 0.3,
        top_k: int = 10
    ) -> List[Dict]:
        """
        语义搜索先例

        Args:
            query: 查询文本
            threshold: 相似度阈值（0-1）
            top_k: 返回前 K 个结果

        Returns:
            list: 相关先例列表
        """
        if not self.precedents or self.tfidf_matrix is None:
            return []

        # 向量化查询
        query_vec = self.vectorizer.transform([query])

        # 计算相似度
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # 过滤和排序
        results = []
        for idx, sim in enumerate(similarities):
            if sim >= threshold:
                precedent = self.precedents[idx]
                results.append({
                    "precedent": precedent,
                    "similarity": float(sim),
                    "weight": precedent.precedent_weight
                })

        # 按相似度和权重排序
        results.sort(
            key=lambda x: (x["similarity"], x["weight"]),
            reverse=True
        )

        return results[:top_k]

    def get_by_id(self, decision_id: str) -> Optional[Precedent]:
        """
        根据 ID 获取先例

        Args:
            decision_id: 决策 ID

        Returns:
            Precedent | None: 先例对象
        """
        for precedent in self.precedents:
            if precedent.decision_id == decision_id:
                return precedent
        return None

    def update_weight(self, decision_id: str, weight: float):
        """
        更新先例权重

        Args:
            decision_id: 决策 ID
            weight: 新权重（0-5）
        """
        precedent = self.get_by_id(decision_id)
        if precedent:
            precedent.precedent_weight = max(0, min(weight, 5))
            self.save()

    def increment_citation(self, decision_id: str):
        """
        增加引用次数

        Args:
            decision_id: 决策 ID
        """
        precedent = self.get_by_id(decision_id)
        if precedent:
            precedent.citation_count += 1
            # 重新计算权重
            new_weight = calculate_precedent_weight(precedent)
            precedent.precedent_weight = new_weight
            self.save()

    def mark_as_precedent(self, decision_id: str, weight: float = 1.0):
        """
        标记为先例

        Args:
            decision_id: 决策 ID
            weight: 初始权重（0-5）
        """
        precedent = self.get_by_id(decision_id)
        if precedent:
            precedent.precedent = True
            precedent.precedent_weight = max(0, min(weight, 5))
            self.save()

    def get_stats(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            dict: 统计信息
        """
        total = len(self.precedents)
        marked = sum(1 for p in self.precedents if p.precedent)
        super_precedents = sum(
            1 for p in self.precedents
            if p.precedent_weight >= 5.0
        )

        return {
            "total_precedents": total,
            "marked_precedents": marked,
            "super_precedents": super_precedents,
            "avg_weight": np.mean([p.precedent_weight for p in self.precedents]) if total > 0 else 0
        }


def calculate_precedent_weight(precedent: Precedent) -> float:
    """
    计算先例权重（0-5）

    算法:
    - 如果已标记为先例，直接返回 precedent_weight
    - 否则，计算基础权重 + 引用奖励 - 时间衰减 + 结果调整

    Args:
        precedent: 先例对象

    Returns:
        float: 先例权重（0-5）
    """
    # 如果已标记为先例，直接返回设置的权重
    if precedent.precedent:
        return float(precedent.precedent_weight)

    base_weight = 1.0

    # 引用次数奖励
    citation_bonus = precedent.citation_count * 0.5

    # 时间衰减（每月-0.1，最多-2）
    try:
        decision_time = datetime.fromisoformat(precedent.timestamp)
        age_days = (datetime.now() - decision_time).days
        age_months = age_days / 30
        age_decay = min(age_months * 0.1, 2.0)
    except:
        age_decay = 0

    # 结果调整
    if precedent.global_votes:
        # 有 Global Crits 投票
        approve_count = sum(
            1 for v in precedent.global_votes.values()
            if v.get("vote") == "approve"
        )
        if approve_count >= 2:
            outcome_modifier = 2  # 共识
        else:
            outcome_modifier = 0  # 分裂
    else:
        # 无 Global Crits 投票
        outcome_modifier = 1  # Local Crits 维持

    # 计算总权重
    total_weight = base_weight + citation_bonus - age_decay + outcome_modifier

    # 上限：5.0（超级先例）
    return max(0, min(total_weight, 5))
