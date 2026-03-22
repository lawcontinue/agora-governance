#!/usr/bin/env python3
"""
P0-3修复验证：日常协调判断逻辑
版本: v1.0.0
测试目标: 验证硬编码逻辑修复后的正确性
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from permission_checker import PermissionChecker


class TestDailyCoordinationLogic(unittest.TestCase):
    """日常协调判断逻辑测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.checker = PermissionChecker()

    def test_daily_coordination_low_resource(self):
        """测试1: 低资源投入（<2小时）→ 日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1
        })
        self.assertTrue(result)

    def test_daily_coordination_high_resource(self):
        """测试2: 高资源投入（≥2小时）→ 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 3
        })
        self.assertFalse(result)

    def test_daily_coordination_no_security_risk(self):
        """测试3: 无安全风险 → 日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'security_risk': False
        })
        self.assertTrue(result)

    def test_daily_coordination_with_security_risk(self):
        """测试4: 有安全风险 → 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'security_risk': True
        })
        self.assertFalse(result)

    def test_daily_coordination_affects_stability(self):
        """测试5: 影响稳定性 → 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'affects_stability': True
        })
        self.assertFalse(result)

    def test_daily_coordination_modifies_architecture(self):
        """测试6: 修改架构 → 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'modifies_core_architecture': True
        })
        self.assertFalse(result)

    def test_daily_coordination_modifies_soul(self):
        """测试7: 修改SOUL → 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'modifies_soul': True
        })
        self.assertFalse(result)

    def test_daily_coordination_all_checks_pass(self):
        """测试8: 所有检查通过 → 日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'security_risk': False,
            'affects_stability': False,
            'modifies_core_architecture': False,
            'modifies_soul': False
        })
        self.assertTrue(result)

    def test_daily_coordination_no_context(self):
        """测试9: 无context参数 → 日常协调（默认）"""
        result = self.checker._is_daily_coordination()
        self.assertTrue(result)

    def test_daily_coordination_empty_context(self):
        """测试10: 空context → 日常协调（默认）"""
        result = self.checker._is_daily_coordination({})
        self.assertTrue(result)

    def test_crit_cannot_veto_daily_coordination(self):
        """测试11: Crit不能否决日常协调"""
        # 场景：Crit尝试否决日常协调工作
        allowed, reason = self.checker.check_permission(
            "critic",
            "veto",
            context={
                'resource_hours': 1,
                'security_risk': False,
                'affects_stability': False
            }
        )
        # 应该被拒绝（不能否决日常协调）
        self.assertFalse(allowed)
        self.assertIn("不能否决日常协调工作", reason)

    def test_crit_can_veto_major_decision(self):
        """测试12: Crit可以否决重大决策"""
        # 场景：Crit否决重大决策（高资源投入）
        allowed, reason = self.checker.check_permission(
            "critic",
            "veto",
            context={
                'resource_hours': 3,  # ≥2小时，非日常协调
                'security_risk': False,
                'veto_reason': '过度自信偏差风险'
            }
        )
        # 应该被允许（可以否决重大决策）
        self.assertTrue(allowed)

    def test_boundary_case_2_hours(self):
        """测试13: 边界情况（恰好2小时）→ 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 2
        })
        self.assertFalse(result)

    def test_boundary_case_1_99_hours(self):
        """测试14: 边界情况（1.99小时）→ 日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1.99
        })
        self.assertTrue(result)

    def test_multiple_risk_factors(self):
        """测试15: 多个风险因素 → 非日常协调"""
        result = self.checker._is_daily_coordination({
            'resource_hours': 1,
            'security_risk': True,
            'affects_stability': True,
            'modifies_core_architecture': False,
            'modifies_soul': False
        })
        # 即使只有一个风险因素，也应该是False
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
