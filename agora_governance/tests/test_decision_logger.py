#!/usr/bin/env python3
"""
决策记录系统单元测试
版本: v1.0.0
测试目标: ≥80% 覆盖率
"""

import unittest
import os
import json
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from decision_logger import DecisionLogger


class TestDecisionLogger(unittest.TestCase):
    """决策记录器测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 使用临时文件进行测试
        cls.temp_log = Path(__file__).parent.parent / "test_decisions.json"
        cls.logger = DecisionLogger(str(cls.temp_log))

    def setUp(self):
        """每个测试前的准备"""
        # 清空测试日志
        self.logger.decisions = []
        self.logger._save_decisions()

    def tearDown(self):
        """每个测试后的清理"""
        # 清空测试日志
        self.logger.decisions = []
        self.logger._save_decisions()

    @classmethod
    def tearDownClass(cls):
        """测试类结束后的清理"""
        # 删除临时文件
        if cls.temp_log.exists():
            os.remove(cls.temp_log)

    def test_record_decision_without_veto(self):
        """测试1: 记录无否决决策"""
        decision_id = self.logger.record_decision(
            decision="实施CoM v5.0引用预测",
            participants=["themis", "critic", "athena"],
            reasoning="原型验证成功，预期收益+7-12%",
            expected_outcome="Token节省-75%"
        )

        self.assertIsNotNone(decision_id)
        self.assertIn("2026-03-17", decision_id)

        # 验证决策已记录
        decision = self.logger.query_decision(decision_id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision['decision'], "实施CoM v5.0引用预测")
        self.assertFalse(decision['crit_veto'])

    def test_record_decision_with_veto(self):
        """测试2: 记录有否决决策"""
        decision_id = self.logger.record_decision(
            decision="实施自适应权重系统",
            participants=["themis", "critic"],
            reasoning="理论预期收益+15-20%",
            crit_veto=True,
            veto_reason="Crit发现过度自信偏差风险",
            expected_outcome="性能提升+15-20%"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertTrue(decision['crit_veto'])
        self.assertEqual(decision['veto_reason'], "Crit发现过度自信偏差风险")

    def test_query_decision_by_id(self):
        """测试3: 按ID查询决策"""
        decision_id = self.logger.record_decision(
            decision="测试决策",
            participants=["themis"],
            reasoning="测试理由"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision['decision_id'], decision_id)
        self.assertEqual(decision['decision'], "测试决策")

    def test_query_nonexistent_decision(self):
        """测试4: 查询不存在的决策"""
        decision = self.logger.query_decision("2026-03-17-999")
        self.assertIsNone(decision)

    def test_query_by_participant(self):
        """测试5: 按参与者查询"""
        # 记录多个决策
        self.logger.record_decision(
            decision="决策1",
            participants=["themis", "athena"],
            reasoning="理由1"
        )
        self.logger.record_decision(
            decision="决策2",
            participants=["athena", "aria"],
            reasoning="理由2"
        )
        self.logger.record_decision(
            decision="决策3",
            participants=["themis", "critic"],
            reasoning="理由3"
        )

        # 查询忒弥斯参与的决策
        themis_decisions = self.logger.query_by_participant("themis")
        self.assertEqual(len(themis_decisions), 2)

        # 查询雅典娜参与的决策
        athena_decisions = self.logger.query_by_participant("athena")
        self.assertEqual(len(athena_decisions), 2)

    def test_query_by_date(self):
        """测试6: 按日期查询"""
        today = "2026-03-17"
        self.logger.record_decision(
            decision="今日决策",
            participants=["themis"],
            reasoning="今日理由"
        )

        today_decisions = self.logger.query_by_date(today)
        self.assertGreater(len(today_decisions), 0)

    def test_query_by_veto_true(self):
        """测试7: 查询有否决的决策"""
        self.logger.record_decision(
            decision="无否决决策",
            participants=["themis"],
            reasoning="理由"
        )
        self.logger.record_decision(
            decision="有否决决策",
            participants=["themis", "critic"],
            reasoning="理由",
            crit_veto=True,
            veto_reason="否决理由"
        )

        vetoed_decisions = self.logger.query_by_veto(True)
        self.assertEqual(len(vetoed_decisions), 1)
        self.assertTrue(vetoed_decisions[0]['crit_veto'])

    def test_query_by_veto_false(self):
        """测试8: 查询无否决的决策"""
        self.logger.record_decision(
            decision="无否决决策1",
            participants=["themis"],
            reasoning="理由"
        )
        self.logger.record_decision(
            decision="有否决决策",
            participants=["themis", "critic"],
            reasoning="理由",
            crit_veto=True,
            veto_reason="否决理由"
        )
        self.logger.record_decision(
            decision="无否决决策2",
            participants=["athena"],
            reasoning="理由"
        )

        non_vetoed_decisions = self.logger.query_by_veto(False)
        self.assertEqual(len(non_vetoed_decisions), 2)

    def test_update_outcome_to_verified(self):
        """测试9: 更新决策结果为已验证"""
        decision_id = self.logger.record_decision(
            decision="测试决策",
            participants=["themis"],
            reasoning="测试理由",
            expected_outcome="预期结果"
        )

        self.logger.update_outcome(
            decision_id,
            actual_outcome="Token节省-68%（实测）",
            status="verified"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertEqual(decision['actual_outcome'], "Token节省-68%（实测）")
        self.assertEqual(decision['status'], "verified")
        self.assertIn('verified_time', decision)

    def test_update_outcome_to_failed(self):
        """测试10: 更新决策结果为失败"""
        decision_id = self.logger.record_decision(
            decision="测试决策",
            participants=["themis"],
            reasoning="测试理由",
            expected_outcome="预期结果"
        )

        self.logger.update_outcome(
            decision_id,
            actual_outcome="实际失败",
            status="failed"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertEqual(decision['status'], "failed")

    def test_update_nonexistent_decision(self):
        """测试11: 更新不存在的决策"""
        with self.assertRaises(ValueError):
            self.logger.update_outcome(
                "2026-03-17-999",
                actual_outcome="测试"
            )

    def test_get_statistics_empty(self):
        """测试12: 获取空统计信息"""
        stats = self.logger.get_statistics()
        self.assertEqual(stats['total_decisions'], 0)
        self.assertEqual(stats['vetoed_decisions'], 0)
        self.assertEqual(stats['verified_decisions'], 0)

    def test_get_statistics_with_data(self):
        """测试13: 获取有数据的统计信息"""
        # 记录多个决策
        self.logger.record_decision(
            decision="决策1",
            participants=["themis"],
            reasoning="理由1"
        )
        self.logger.record_decision(
            decision="决策2",
            participants=["themis", "critic"],
            reasoning="理由2",
            crit_veto=True,
            veto_reason="否决"
        )

        decision_id = self.logger.record_decision(
            decision="决策3",
            participants=["athena"],
            reasoning="理由3"
        )
        self.logger.update_outcome(
            decision_id,
            actual_outcome="成功",
            status="verified"
        )

        stats = self.logger.get_statistics()
        self.assertEqual(stats['total_decisions'], 3)
        self.assertEqual(stats['vetoed_decisions'], 1)
        self.assertEqual(stats['verified_decisions'], 1)
        self.assertEqual(stats['veto_rate'], "33.3%")

    def test_decision_id_format(self):
        """测试14: 决策ID格式正确"""
        decision_id = self.logger.record_decision(
            decision="测试",
            participants=["themis"],
            reasoning="理由"
        )

        # 验证ID格式：YYYY-MM-DD-XXX
        parts = decision_id.split('-')
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "2026")
        self.assertEqual(parts[1], "03")
        self.assertEqual(parts[2], "17")

    def test_decision_persistence(self):
        """测试15: 决策持久化"""
        decision_id = self.logger.record_decision(
            decision="持久化测试",
            participants=["themis"],
            reasoning="测试持久化"
        )

        # 创建新的logger实例
        new_logger = DecisionLogger(str(self.temp_log))

        # 验证决策已持久化
        decision = new_logger.query_decision(decision_id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision['decision'], "持久化测试")

    def test_context_storage(self):
        """测试16: 上下文信息存储"""
        context = {
            "resource_hours": 3,
            "security_risk": False,
            "custom_field": "自定义值"
        }

        decision_id = self.logger.record_decision(
            decision="上下文测试",
            participants=["themis"],
            reasoning="测试上下文",
            context=context
        )

        decision = self.logger.query_decision(decision_id)
        self.assertEqual(decision['context'], context)

    def test_default_status(self):
        """测试17: 默认状态为pending"""
        decision_id = self.logger.record_decision(
            decision="默认状态测试",
            participants=["themis"],
            reasoning="测试"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertEqual(decision['status'], "pending")

    def test_json_format_valid(self):
        """测试18: JSON格式有效"""
        self.logger.record_decision(
            decision="JSON测试",
            participants=["themis"],
            reasoning="测试JSON格式"
        )

        # 验证JSON文件格式正确
        with open(self.temp_log, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_unicode_support(self):
        """测试19: Unicode支持"""
        decision_id = self.logger.record_decision(
            decision="测试中文🔮💻",
            participants=["themis", "雅典娜", "Aria"],
            reasoning="测试Emoji和中文：✅通过❌失败",
            expected_outcome="预期收益💰+15-20%"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertIn("🔮", decision['decision'])
        self.assertIn("雅典娜", decision['participants'])

    def test_multiple_updates(self):
        """测试20: 多次更新决策结果"""
        decision_id = self.logger.record_decision(
            decision="多次更新测试",
            participants=["themis"],
            reasoning="测试"
        )

        # 第一次更新
        self.logger.update_outcome(
            decision_id,
            actual_outcome="第一次更新",
            status="verified"
        )

        # 第二次更新
        self.logger.update_outcome(
            decision_id,
            actual_outcome="第二次更新",
            status="failed"
        )

        decision = self.logger.query_decision(decision_id)
        self.assertEqual(decision['actual_outcome'], "第二次更新")
        self.assertEqual(decision['status'], "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
