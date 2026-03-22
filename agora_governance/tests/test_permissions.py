#!/usr/bin/env python3
"""
权限检查系统单元测试
版本: v1.0.0
测试目标: ≥80% 覆盖率
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from permission_checker import PermissionChecker


class TestPermissionChecker(unittest.TestCase):
    """权限检查器测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.checker = PermissionChecker()

    def test_themis_coordinate_collaboration_allowed(self):
        """测试1: 忒弥斯协调协作权限（应该通过）"""
        result, reason = self.checker.check_permission("themis", "coordinate_collaboration")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_themis_code_modify_denied(self):
        """测试2: 忒弥斯修改代码权限（应该拒绝）"""
        result, reason = self.checker.check_permission("themis", "code_modify")
        self.assertFalse(result)
        self.assertIn("无权", reason)
        self.assertIn("宪法第4条", reason)

    def test_themis_major_decision_without_crit_denied(self):
        """测试3: 忒弥斯重大决策未咨询Crit（应该拒绝）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"affects_stability": True, "crit_consulted": False}
        )
        self.assertFalse(result)
        self.assertIn("必须先咨询Crit", reason)
        self.assertIn("宪法第5条", reason)

    def test_themis_major_decision_with_crit_allowed(self):
        """测试4: 忒弥斯重大决策已咨询Crit（应该通过）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"affects_stability": True, "crit_consulted": True}
        )
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_themis_risk_forecast_allowed(self):
        """测试5: 忒弥斯风险预见权限（应该通过）"""
        result, reason = self.checker.check_permission("themis", "risk_forecast")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_themis_architecture_design_allowed(self):
        """测试6: 忒弥斯架构设计权限（应该通过）"""
        result, reason = self.checker.check_permission("themis", "architecture_design")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_critic_veto_without_reason_denied(self):
        """测试7: Crit否决未提供理由（应该拒绝）"""
        result, reason = self.checker.check_permission(
            "critic",
            "veto",
            context={
                "veto_reason": "",
                "resource_hours": 3  # 重大决策（≥2小时）
            }
        )
        self.assertFalse(result)
        self.assertIn("必须提供否决理由", reason)
        self.assertIn("宪法第10条", reason)

    def test_critic_veto_with_reason_allowed(self):
        """测试8: Crit否决提供理由（应该通过）"""
        result, reason = self.checker.check_permission(
            "critic",
            "veto",
            context={
                "veto_reason": "发现过度自信偏差",
                "resource_hours": 3  # 重大决策（≥2小时）
            }
        )
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_critic_require_reasoning_allowed(self):
        """测试9: Crit要求提供依据权限（应该通过）"""
        result, reason = self.checker.check_permission("critic", "require_reasoning")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_critic_initiate_project_denied(self):
        """测试10: Crit发起项目权限（应该拒绝）"""
        result, reason = self.checker.check_permission("critic", "initiate_project")
        self.assertFalse(result)
        self.assertIn("无权", reason)
        self.assertIn("宪法第4条", reason)

    def test_code_modify_soul_denied(self):
        """测试11: Code修改SOUL权限（应该拒绝）"""
        result, reason = self.checker.check_permission("code", "modify_soul")
        self.assertFalse(result)
        self.assertIn("无权", reason)
        self.assertIn("宪法第4条", reason)

    def test_code_implementation_allowed(self):
        """测试12: Code代码实现权限（应该通过）"""
        result, reason = self.checker.check_permission("code", "code_implementation")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_code_refactoring_allowed(self):
        """测试13: Code代码重构权限（应该通过）"""
        result, reason = self.checker.check_permission("code", "code_refactoring")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_code_technical_design_allowed(self):
        """测试14: Code技术方案设计权限（应该通过）"""
        result, reason = self.checker.check_permission("code", "technical_design")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_athena_data_analysis_allowed(self):
        """测试15: 雅典娜数据分析权限（应该通过）"""
        result, reason = self.checker.check_permission("athena", "data_analysis")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_athena_quantitative_modeling_allowed(self):
        """测试16: 雅典娜量化建模权限（应该通过）"""
        result, reason = self.checker.check_permission("athena", "quantitative_modeling")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_athena_system_config_denied(self):
        """测试17: 雅典娜系统配置权限（应该拒绝）"""
        result, reason = self.checker.check_permission("athena", "system_config")
        self.assertFalse(result)
        self.assertIn("无权", reason)
        self.assertIn("宪法第4条", reason)

    def test_aria_ui_ux_design_allowed(self):
        """测试18: Aria UI/UX设计权限（应该通过）"""
        result, reason = self.checker.check_permission("aria", "ui_ux_design")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_aria_creative_output_allowed(self):
        """测试19: Aria创意输出权限（应该通过）"""
        result, reason = self.checker.check_permission("aria", "creative_output")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_aria_rapid_prototyping_allowed(self):
        """测试20: Aria快速原型权限（应该通过）"""
        result, reason = self.checker.check_permission("aria", "rapid_prototyping")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_shield_security_audit_allowed(self):
        """测试21: Shield安全审计权限（应该通过）"""
        result, reason = self.checker.check_permission("shield", "security_audit")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_shield_vulnerability_scan_allowed(self):
        """测试22: Shield漏洞扫描权限（应该通过）"""
        result, reason = self.checker.check_permission("shield", "vulnerability_scan")
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_shield_modify_policy_denied(self):
        """测试23: Shield修改安全策略权限（应该拒绝）"""
        result, reason = self.checker.check_permission("shield", "modify_policy")
        self.assertFalse(result)
        self.assertIn("无权", reason)
        self.assertIn("宪法第4条", reason)

    def test_unknown_agent_denied(self):
        """测试24: 未知Agent（应该拒绝）"""
        result, reason = self.checker.check_permission("unknown", "any_action")
        self.assertFalse(result)
        self.assertIn("未知Agent", reason)

    def test_themis_security_risk_decision_without_crit_denied(self):
        """测试25: 忒弥斯安全风险决策未咨询Crit（应该拒绝）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"security_risk": True, "crit_consulted": False}
        )
        self.assertFalse(result)
        self.assertIn("必须先咨询Crit", reason)

    def test_themis_resource_heavy_decision_without_crit_denied(self):
        """测试26: 忒弥斯资源密集决策未咨询Crit（应该拒绝）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"resource_hours": 3, "crit_consulted": False}
        )
        self.assertFalse(result)
        self.assertIn("必须先咨询Crit", reason)

    def test_themis_architecture_modify_without_crit_denied(self):
        """测试27: 忒弥斯架构修改决策未咨询Crit（应该拒绝）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"modifies_core_architecture": True, "crit_consulted": False}
        )
        self.assertFalse(result)
        self.assertIn("必须先咨询Crit", reason)

    def test_minor_decision_without_crit_allowed(self):
        """测试28: 日常决策无需咨询Crit（应该通过）"""
        result, reason = self.checker.check_permission(
            "themis",
            "final_decision",
            context={"resource_hours": 1, "security_risk": False}
        )
        self.assertTrue(result)
        self.assertIn("有权限", reason)

    def test_get_agent_permissions(self):
        """测试29: 获取Agent权限配置"""
        permissions = self.checker.get_agent_permissions("themis")
        self.assertIn("name", permissions)
        self.assertIn("permissions", permissions)
        self.assertIn("restrictions", permissions)
        self.assertIn("obligations", permissions)
        self.assertEqual(permissions["name"], "忒弥斯")

    def test_get_unknown_agent_permissions(self):
        """测试30: 获取未知Agent权限配置"""
        permissions = self.checker.get_agent_permissions("unknown")
        self.assertEqual(permissions, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
