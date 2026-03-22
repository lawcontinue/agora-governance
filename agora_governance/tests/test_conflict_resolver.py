#!/usr/bin/env python3
"""
冲突解决流程单元测试
版本: v1.0.0
测试目标: ≥80% 覆盖率
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from conflict_resolver import ConflictResolver
from permission_checker import PermissionChecker
from decision_logger import DecisionLogger


class TestConflictResolver(unittest.TestCase):
    """冲突解决器测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.permission_checker = PermissionChecker()
        cls.decision_logger = DecisionLogger()
        cls.resolver = ConflictResolver(
            permission_checker=cls.permission_checker,
            decision_logger=cls.decision_logger
        )

    def test_p1_conflict_negotiate(self):
        """测试1: P1冲突建议自行协商"""
        result = self.resolver.resolve_conflict(
            level="P1",
            agents=["athena", "aria"],
            description="优先级排序分歧"
        )

        self.assertEqual(result['resolution'], "negotiate")
        self.assertIn("自行协商", result['reason'])
        self.assertEqual(result['resolved_by'], ["athena", "aria"])
        self.assertEqual(result['timeout_minutes'], 30)

    def test_p2_conflict_coordinate(self):
        """测试2: P2冲突忒弥斯协调"""
        result = self.resolver.resolve_conflict(
            level="P2",
            agents=["code", "aria"],
            description="接口定义分歧"
        )

        self.assertEqual(result['resolution'], "coordinate")
        self.assertIn("忒弥斯协调", result['reason'])
        self.assertEqual(result['resolved_by'], "themis")
        self.assertEqual(result['timeout_minutes'], 120)

    def test_p0_conflict_crit_veto(self):
        """测试3: P0冲突Crit否决"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="实施自适应权重系统",
            context={
                "has_claims": True,
                "has_measured_data": False
            }
        )

        self.assertEqual(result['resolution'], "veto")
        self.assertIn("Crit否决", result['reason'])
        self.assertEqual(result['resolved_by'], "critic")
        self.assertIn('veto_reason', result)

    def test_p0_conflict_override(self):
        """测试4: P0冲突忒弥斯推翻"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="实施CoM v5.0",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "has_measured_data": True,
                "override_reason": "原型验证成功，预期收益+7-12%",
                "proposed_decision": "实施CoM v5.0引用预测"
            }
        )

        self.assertEqual(result['resolution'], "override")
        self.assertIn("忒弥斯最终决策", result['reason'])
        self.assertEqual(result['resolved_by'], "themis")
        self.assertIn('decision', result)

    def test_p0_conflict_coordinate_when_no_veto(self):
        """测试5: P0冲突无否决时协调"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="安全改进建议",
            context={
                "has_claims": False,
                "risk_assessed": True
            }
        )

        self.assertEqual(result['resolution'], "coordinate")
        self.assertEqual(result['resolved_by'], "themis")

    def test_unknown_conflict_level(self):
        """测试6: 未知冲突级别"""
        result = self.resolver.resolve_conflict(
            level="P3",
            agents=["themis"],
            description="测试"
        )

        self.assertEqual(result['resolution'], "error")
        self.assertIn("未知冲突级别", result['reason'])

    def test_p2_without_permission_checker(self):
        """测试7: P2冲突无权限检查器"""
        resolver = ConflictResolver(permission_checker=None)
        result = resolver.resolve_conflict(
            level="P2",
            agents=["code", "aria"],
            description="接口定义分歧"
        )

        self.assertEqual(result['resolution'], "coordinate")

    def test_overconfidence_detection(self):
        """测试8: 过度自信偏差检测"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="声称改进20%但无数据",
            context={
                "has_claims": True,
                "has_measured_data": False
            }
        )

        self.assertEqual(result['resolution'], "veto")
        self.assertIn("过度自信偏差", result['veto_reason'])

    def test_unassessed_risk_detection(self):
        """测试9: 未评估风险检测"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="重大风险未评估",
            context={
                "risk_assessed": False
            }
        )

        self.assertEqual(result['resolution'], "veto")
        self.assertIn("重大风险", result['veto_reason'])

    def test_unconstitutional_detection(self):
        """测试10: 违反宪法检测"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="违反宪法原则",
            context={
                "unconstitutional": True
            }
        )

        self.assertEqual(result['resolution'], "veto")
        self.assertIn("违反宪法", result['veto_reason'])

    def test_override_conditions_all_met(self):
        """测试11: 所有推翻条件满足"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="满足所有推翻条件",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "has_measured_data": True,
                "override_reason": "实测数据显示可行"
            }
        )

        self.assertEqual(result['resolution'], "override")
        self.assertIn("满足所有推翻条件", result['reason'])

    def test_override_conditions_partial(self):
        """测试12: 部分推翻条件满足"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="仅部分推翻条件",
            context={
                "risk_assessed": True,
                "risk_acceptable": True
            }
        )

        # 不应该推翻（条件不全）
        self.assertNotEqual(result['resolution'], "override")

    def test_override_with_reviewer_approval(self):
        """测试13: 使用Reviewer批准推翻"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="Reviewer批准",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "reviewer_approved": True,
                "override_reason": "Reviewer Agent批准"
            }
        )

        self.assertEqual(result['resolution'], "override")
        self.assertIn("Reviewer批准", result['reason'])

    def test_override_with_written_responsibility(self):
        """测试14: 使用书面责任推翻"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="承担书面责任",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "accept_written_responsibility": True,
                "override_reason": "忒弥斯承担书面责任"
            }
        )

        self.assertEqual(result['resolution'], "override")
        self.assertIn("书面责任", result['reason'])

    def test_action_items_p1(self):
        """测试15: P1冲突行动项"""
        result = self.resolver.resolve_conflict(
            level="P1",
            agents=["athena", "aria"],
            description="优先级排序分歧"
        )

        self.assertGreater(len(result['action_items']), 0)
        self.assertIn("协商", result['action_items'][0])

    def test_action_items_p2(self):
        """测试16: P2冲突行动项"""
        result = self.resolver.resolve_conflict(
            level="P2",
            agents=["code", "aria"],
            description="接口定义分歧"
        )

        self.assertGreater(len(result['action_items']), 0)
        self.assertIn("忒弥斯介入", result['action_items'][0])

    def test_action_items_p0_veto(self):
        """测试17: P0冲突否决行动项"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="过度自信",
            context={
                "has_claims": True,
                "has_measured_data": False
            }
        )

        self.assertIn("决策暂停", result['action_items'])
        self.assertIn("否决理由", result['action_items'][1])

    def test_action_items_p0_override(self):
        """测试18: P0冲突推翻行动项"""
        result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="实测数据支持",
            context={
                "risk_assessed": True,
                "risk_acceptable": True,
                "has_measured_data": True,
                "override_reason": "原型验证成功",
                "proposed_decision": "实施CoM v5.0"
            }
        )

        self.assertIn("记录到决策日志", result['action_items'])
        self.assertIn("执行决策", result['action_items'][-1])

    def test_timeout_values(self):
        """测试19: 超时时间正确"""
        # P1: 30分钟
        p1_result = self.resolver.resolve_conflict(
            level="P1",
            agents=["athena", "aria"],
            description="测试"
        )
        self.assertEqual(p1_result['timeout_minutes'], 30)

        # P2: 120分钟
        p2_result = self.resolver.resolve_conflict(
            level="P2",
            agents=["code", "aria"],
            description="测试"
        )
        self.assertEqual(p2_result['timeout_minutes'], 120)

        # P0: 240分钟
        p0_result = self.resolver.resolve_conflict(
            level="P0",
            agents=["themis", "athena"],
            description="测试",
            context={"has_claims": False}
        )
        self.assertEqual(p0_result['timeout_minutes'], 240)

    def test_multiple_agents_in_p1(self):
        """测试20: P1冲突多个Agent"""
        result = self.resolver.resolve_conflict(
            level="P1",
            agents=["athena", "aria", "code", "shield"],
            description="多方优先级分歧"
        )

        self.assertEqual(result['resolution'], "negotiate")
        self.assertEqual(len(result['resolved_by']), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
