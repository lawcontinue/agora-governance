#!/usr/bin/env python3
"""
Agora治理层集成测试
测试真实场景下的Multi-Agent协作
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from permission_checker import PermissionChecker
from decision_logger import DecisionLogger
from conflict_resolver import ConflictResolver


class TestAgoraGovernanceIntegration(unittest.TestCase):
    """Agora治理层集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.permission_checker = PermissionChecker()
        cls.decision_logger = DecisionLogger()
        cls.resolver = ConflictResolver(
            permission_checker=cls.permission_checker,
            decision_logger=cls.decision_logger
        )

    def test_scenario_1_major_decision_without_crit(self):
        """
        场景1: 忒弥斯重大决策未咨询Crit

        期望: 权限拒绝 + Crit建议
        """
        # 步骤1: 检查权限
        allowed, reason = self.permission_checker.check_permission(
            "themis",
            "final_decision",
            context={
                "affects_stability": True,
                "crit_consulted": False
            }
        )
        self.assertFalse(allowed)
        self.assertIn("必须先咨询Crit", reason)

        # 步骤2: 如果强制执行，触发P0冲突
        conflict = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="重大决策未咨询Crit",
            context={"risk_assessed": False}
        )
        self.assertEqual(conflict['resolution'], "veto")

    def test_scenario_2_code_try_to_modify_soul(self):
        """
        场景2: Code尝试修改SOUL

        期望: 权限拒绝 + 无法执行
        """
        allowed, reason = self.permission_checker.check_permission(
            "code",
            "modify_soul"
        )
        self.assertFalse(allowed)
        self.assertIn("无权修改SOUL", reason)

    def test_scenario_3_overconfidence_detected(self):
        """
        场景3: 过度自信偏差检测

        期望: Crit否决
        """
        conflict = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="声称改进20%但无数据",
            context={
                "has_claims": True,
                "has_measured_data": False
            }
        )
        self.assertEqual(conflict['resolution'], "veto")
        self.assertIn("过度自信偏差", conflict['veto_reason'])

    def test_scenario_4_themis_override_with_measured_data(self):
        """
        场景4: 忒弥斯用实测数据推翻否决

        期望: 推翻成功
        """
        conflict = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="原型验证成功",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "has_measured_data": True,
                "override_reason": "原型测试通过，Token节省-68%",
                "proposed_decision": "实施CoM v5.0"
            }
        )
        self.assertEqual(conflict['resolution'], "override")
        self.assertIn("满足所有推翻条件", conflict['reason'])

    def test_scenario_5_p1_conflict_self_resolution(self):
        """
        场景5: P1冲突自行解决

        期望: 建议协商
        """
        conflict = self.resolver.resolve_conflict(
            level="P1",
            agents=["athena", "aria"],
            description="优先级排序分歧"
        )
        self.assertEqual(conflict['resolution'], "negotiate")
        self.assertEqual(conflict['timeout_minutes'], 30)

    def test_scenario_6_decision_lifecycle(self):
        """
        场景6: 完整决策生命周期

        期望: 记录 → 查询 → 更新
        """
        # 记录决策
        decision_id = self.decision_logger.record_decision(
            decision="测试决策",
            participants=["themis", "athena"],
            reasoning="测试理由",
            expected_outcome="预期结果"
        )
        self.assertIsNotNone(decision_id)

        # 查询决策
        decision = self.decision_logger.query_decision(decision_id)
        self.assertEqual(decision['decision'], "测试决策")

        # 更新结果
        self.decision_logger.update_outcome(
            decision_id,
            actual_outcome="实际结果",
            status="verified"
        )
        updated = self.decision_logger.query_decision(decision_id)
        self.assertEqual(updated['actual_outcome'], "实际结果")
        self.assertEqual(updated['status'], "verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
