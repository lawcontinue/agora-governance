"""
Agora 2.0 幻觉检测器（轻量级实现）

基于论文: HalluGuard: Demystifying Data-Driven and Reasoning-Driven Hallucinations in LLMs
来源: ICLR 2026（arXiv: 2601.18753）

两大幻觉类型:
1. 数据驱动型幻觉（Data-driven）: 模型"本来就不知道，却说得很像真的"
2. 推理驱动型幻觉（Reasoning-driven）: 模型"一开始对，但越推越歪"

核心理念:
- 幻觉不是"突然出现"，而是"被一步步推出来的"
- 推理驱动型幻觉会随推理长度指数级放大
- 数据驱动型幻觉源于知识缺失、偏差、分布错配

实现策略（轻量级）:
- 不依赖复杂的 NTK 几何结构
- 使用启发式规则检测幻觉信号
- 集成到 ErrorPreventionChecklistAnalyzer
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class HallucinationType(Enum):
    """幻觉类型"""
    DATA_DRIVEN = "data_driven"  # 数据驱动型
    REASONING_DRIVEN = "reasoning_driven"  # 推理驱动型
    UNKNOWN = "unknown"


@dataclass
class HallucinationSignal:
    """幻觉信号"""
    type: HallucinationType
    severity: float  # 0.0-1.0
    description: str
    evidence: str


class HallucinationDetector:
    """
    轻量级幻觉检测器

    核心功能:
    1. 检测数据驱动型幻觉信号
    2. 检测推理驱动型幻觉信号
    3. 生成幻觉风险报告
    """

    def __init__(self):
        """初始化幻觉检测器"""
        # 数据驱动型幻觉信号模式
        self.data_driven_patterns = [
            # 知识缺失信号
            r"我相信.*?应该是",  # 缺乏确凿证据的推断
            r"根据.*?推测",  # 推测性陈述
            r"可能是",  # 不确定陈述

            # 偏差信号
            r"所有人.*?都",  # 过度概括
            r"从来没有",  # 绝对化陈述
            r"总是.*?这样",  # 绝对化陈述

            # 分布错配信号
            r"根据.*?年.*?的数据.*?现在.*?",  # 过时数据
            r"在.*?地区.*?也是.*?",  # 地域泛化
        ]

        # 推理驱动型幻觉信号模式
        self.reasoning_driven_patterns = [
            # 多步推理链信号
            r"首先.*?那么.*?然后.*?因此",  # 长推理链
            r"那么.*?然后.*?那么",  # 长推理链
            r"因此.*?所以.*?因此",  # 长推理链

            # 逻辑不一致信号
            r"虽然.*?但是.*?然而",  # 多重转折
            r"一方面.*?另一方面.*?但是",  # 自相矛盾

            # 幻觉放大信号
            r"肯定.*?必然",  # 过度推断
            r"毫无疑问",  # 过度自信
            r"显而易见",  # 过度自信
        ]

    def detect_data_driven(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[HallucinationSignal]:
        """
        检测数据驱动型幻觉信号

        Args:
            text: 待检测文本
            context: 上下文信息（可选）

        Returns:
            幻觉信号列表
        """
        signals = []

        # 检查知识缺失信号
        for pattern in self.data_driven_patterns[:3]:  # 知识缺失信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.DATA_DRIVEN,
                    severity=0.6,  # 中等严重度
                    description=f"检测到知识缺失信号: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        # 检查偏差信号
        for pattern in self.data_driven_patterns[3:6]:  # 偏差信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.DATA_DRIVEN,
                    severity=0.7,  # 较高严重度
                    description=f"检测到偏差信号: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        # 检查分布错配信号
        for pattern in self.data_driven_patterns[6:]:  # 分布错配信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.DATA_DRIVEN,
                    severity=0.8,  # 高严重度
                    description=f"检测到分布错配信号: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        return signals

    def detect_reasoning_driven(
        self,
        text: str,
        reasoning_length: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> List[HallucinationSignal]:
        """
        检测推理驱动型幻觉信号

        Args:
            text: 待检测文本
            reasoning_length: 推理长度（句子数）
            context: 上下文信息（可选）

        Returns:
            幻觉信号列表
        """
        signals = []

        # 检查推理长度（论文关键发现：推理驱动型幻觉随长度指数级放大）
        if reasoning_length > 5:  # 超过 5 句话
            signals.append(HallucinationSignal(
                type=HallucinationType.REASONING_DRIVEN,
                severity=0.5 + (reasoning_length - 5) * 0.1,  # 指数增长
                description=f"推理链过长（{reasoning_length} 句），幻觉风险指数级放大",
                evidence=f"推理长度: {reasoning_length}，阈值: 5"
            ))

        # 检查多步推理链信号
        for pattern in self.reasoning_driven_patterns[:2]:  # 多步推理链信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.REASONING_DRIVEN,
                    severity=0.6,  # 中等严重度
                    description=f"检测到多步推理链: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        # 检查逻辑不一致信号
        for pattern in self.reasoning_driven_patterns[2:4]:  # 逻辑不一致信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.REASONING_DRIVEN,
                    severity=0.7,  # 较高严重度
                    description=f"检测到逻辑不一致: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        # 检查幻觉放大信号
        for pattern in self.reasoning_driven_patterns[4:]:  # 幻觉放大信号
            matches = re.findall(pattern, text)
            if matches:
                signals.append(HallucinationSignal(
                    type=HallucinationType.REASONING_DRIVEN,
                    severity=0.8,  # 高严重度
                    description=f"检测到幻觉放大信号: '{matches[0]}'",
                    evidence=f"模式: {pattern}, 匹配: {matches}"
                ))

        return signals

    def detect(
        self,
        text: str,
        reasoning_length: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> List[HallucinationSignal]:
        """
        检测幻觉信号（综合）

        Args:
            text: 待检测文本
            reasoning_length: 推理长度（句子数）
            context: 上下文信息（可选）

        Returns:
            幻觉信号列表（按严重度排序）
        """
        # 检测数据驱动型幻觉
        data_signals = self.detect_data_driven(text, context)

        # 检测推理驱动型幻觉
        reasoning_signals = self.detect_reasoning_driven(text, reasoning_length, context)

        # 合并并按严重度排序
        all_signals = data_signals + reasoning_signals
        all_signals.sort(key=lambda x: x.severity, reverse=True)

        return all_signals

    def calculate_risk_score(
        self,
        signals: List[HallucinationSignal]
    ) -> float:
        """
        计算幻觉风险分数

        Args:
            signals: 幻觉信号列表

        Returns:
            风险分数（0.0-1.0）
        """
        if not signals:
            return 0.0

        # 加权平均（按严重度）
        total_severity = sum(signal.severity for signal in signals)
        avg_severity = total_severity / len(signals)

        # 考虑信号数量（信号越多，风险越高，但有上限）
        signal_count_factor = min(1.0, len(signals) / 5.0)  # 除以 5 而不是 10

        # 综合风险分数
        risk_score = avg_severity * 0.7 + signal_count_factor * 0.3  # 加权组合

        return min(1.0, risk_score)


# 使用示例
if __name__ == "__main__":
    detector = HallucinationDetector()

    # 测试案例 1: 数据驱动型幻觉
    text1 = "我相信这个方法应该是有效的，因为所有人在这个场景下都会这样做。"
    signals1 = detector.detect(text1)
    print(f"文本1: {text1}")
    print(f"检测到 {len(signals1)} 个幻觉信号:")
    for signal in signals1:
        print(f"  - {signal.description} (严重度: {signal.severity})")
    print(f"风险分数: {detector.calculate_risk_score(signals1):.2f}")
    print()

    # 测试案例 2: 推理驱动型幻觉（长推理链）
    text2 = "首先，我们需要考虑X因素，那么Y就会发生，然后Z肯定会这样，因此毫无疑问结果是A。"
    signals2 = detector.detect(text2, reasoning_length=5)
    print(f"文本2: {text2}")
    print(f"检测到 {len(signals2)} 个幻觉信号:")
    for signal in signals2:
        print(f"  - {signal.description} (严重度: {signal.severity})")
    print(f"风险分数: {detector.calculate_risk_score(signals2):.2f}")
    print()

    # 测试案例 3: 无幻觉
    text3 = "根据测试数据（2026-03-23），性能提升了2.36%，置信度95%。"
    signals3 = detector.detect(text3)
    print(f"文本3: {text3}")
    print(f"检测到 {len(signals3)} 个幻觉信号:")
    for signal in signals3:
        print(f"  - {signal.description} (严重度: {signal.severity})")
    print(f"风险分数: {detector.calculate_risk_score(signals3):.2f}")
