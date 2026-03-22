#!/usr/bin/env python3
"""
决策验证机制测试
版本: v1.0.0
测试覆盖率目标: ≥90%

作者: 忒弥斯 (T-Mind)
日期: 2026-03-17
"""

import pytest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from decision_validator import DecisionValidator, ValidationResult, ValidationSeverity
from permission_checker import PermissionChecker
from decision_logger import DecisionLogger


class TestDecisionValidator:
    """决策验证器测试"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        perm_checker = PermissionChecker()
        decision_logger = DecisionLogger()
        return DecisionValidator(perm_checker, decision_logger)

    def test_validate_valid_decision(self, validator):
        """测试有效决策"""
        agent_id = "themis"
        action = "coordinate_collaboration"  # 有效操作
        context = {
            "task": "update_documentation",
            "resource_hours": 1
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert is_valid
        # 允许有 WARNING 或 INFO，但不能有 ERROR 或 CRITICAL
        error_results = [r for r in results if r.severity in [
            ValidationSeverity.ERROR, ValidationSeverity.CRITICAL
        ]]
        assert len(error_results) == 0

    def test_validate_missing_agent_id(self, validator):
        """测试缺失 agent_id"""
        agent_id = ""
        action = "daily_task"
        context = {}

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert not is_valid

        # 应该有 CRITICAL 错误
        critical_results = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_results) > 0
        assert any("agent_id" in r.message for r in critical_results)

    def test_validate_missing_action(self, validator):
        """测试缺失 action"""
        agent_id = "themis"
        action = ""
        context = {}

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert not is_valid

        # 应该有 CRITICAL 错误
        critical_results = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_results) > 0
        assert any("action" in r.message for r in critical_results)

    def test_validate_invalid_context_type(self, validator):
        """测试无效的 context 类型"""
        agent_id = "themis"
        action = "daily_task"
        context = "invalid"  # 应该是 dict

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert not is_valid

        # 应该有 CRITICAL 错误
        critical_results = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical_results) > 0
        assert any("context" in r.message and "字典" in r.message for r in critical_results)

    def test_validate_security_risk_without_mitigation(self, validator):
        """测试高风险操作缺少缓解措施"""
        agent_id = "themis"
        action = "deploy_to_production"
        context = {
            "security_risk": True
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有 WARNING（不是 ERROR，因为只是建议）
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warning_results) > 0
        assert any("mitigation" in r.message or "缓解" in r.message for r in warning_results)

    def test_validate_security_risk_with_mitigation(self, validator):
        """测试高风险操作有缓解措施"""
        agent_id = "themis"
        action = "deploy_to_production"
        context = {
            "security_risk": True,
            "mitigation": "已通过 Code 审查，测试覆盖率 100%"
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 不应该有缓解措施相关的警告
        mitigation_warnings = [
            r for r in results
            if "mitigation" in r.message.lower() and r.severity == ValidationSeverity.WARNING
        ]
        assert len(mitigation_warnings) == 0

    def test_validate_resource_intensive_without_cost(self, validator):
        """测试资源密集型操作缺少成本估算"""
        agent_id = "themis"
        action = "large_refactoring"
        context = {
            "resource_hours": 5
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有 INFO（不是 WARNING，因为只是建议）
        info_results = [r for r in results if r.severity == ValidationSeverity.INFO]
        assert len(info_results) > 0
        assert any("成本" in r.message or "cost" in r.message for r in info_results)

    def test_validate_negative_resource_hours(self, validator):
        """测试负数的 resource_hours"""
        agent_id = "themis"
        action = "daily_task"
        context = {
            "resource_hours": -1
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert not is_valid

        # 应该有 ERROR
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(error_results) > 0
        assert any("resource_hours" in r.field and "负数" in r.message for r in error_results)

    def test_validate_excessive_resource_hours(self, validator):
        """测试过长的 resource_hours"""
        agent_id = "themis"
        action = "large_refactoring"
        context = {
            "resource_hours": 30
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有 WARNING
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warning_results) > 0
        assert any("resource_hours" in r.field and "超过" in r.message for r in warning_results)

    def test_validate_invalid_resource_hours_type(self, validator):
        """测试无效的 resource_hours 类型"""
        agent_id = "themis"
        action = "daily_task"
        context = {
            "resource_hours": "invalid"  # 应该是数值
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        assert not is_valid

        # 应该有 ERROR
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(error_results) > 0
        assert any("resource_hours" in r.field and "数值" in r.message for r in error_results)

    def test_validate_modify_core_architecture_without_fields(self, validator):
        """测试修改核心架构缺少必填字段"""
        agent_id = "themis"
        action = "modify_core_architecture"
        context = {
            "reason": "优化性能"
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有 WARNING（缺少 modifies_core_architecture）
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warning_results) > 0

    def test_validate_modify_core_architecture_with_fields(self, validator):
        """测试修改核心架构有必填字段"""
        agent_id = "themis"
        action = "modify_core_architecture"
        context = {
            "modifies_core_architecture": True,
            "reason": "优化性能"
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 不应该有字段缺失的警告
        field_warnings = [
            r for r in results
            if "context" in r.field and r.severity == ValidationSeverity.WARNING
        ]
        # 可能有其他警告，但不应该有字段缺失
        assert not any("modifies_core_architecture" in str(r.message) for r in field_warnings)

    def test_format_results_empty(self, validator):
        """测试格式化空结果"""
        formatted = validator.format_results([])
        assert "✅" in formatted
        assert "通过" in formatted

    def test_format_results_with_errors(self, validator):
        """测试格式化有错误的结果"""
        results = [
            ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                message="严重错误",
                field="test_field",
                suggestion="修复建议"
            ),
            ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="警告信息"
            )
        ]

        formatted = validator.format_results(results)

        assert "🔴" in formatted or "严重错误" in formatted
        assert "⚠️" in formatted or "警告" in formatted
        assert "test_field" in formatted
        assert "修复建议" in formatted
        assert "📊" in formatted or "统计" in formatted


class TestDecisionValidatorIntegration:
    """集成测试"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        perm_checker = PermissionChecker()
        decision_logger = DecisionLogger()
        return DecisionValidator(perm_checker, decision_logger)

    def test_real_world_scenario_p0_decision(self, validator):
        """测试真实场景：P0 重大决策"""
        agent_id = "themis"
        action = "architecture_design"  # 有效操作
        context = {
            "modifies_core_architecture": True,
            "reason": "重构 Agora 治理层",
            "resource_hours": 8,
            "security_risk": True,
            "mitigation": "100% 测试覆盖 + Reviewer Agent 审查",
            "crit_consulted": True  # 忒弥斯已咨询 Crit
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有效（有缓解措施）
        # 可能有 WARNING，但不应该有 ERROR 或 CRITICAL
        error_results = [r for r in results if r.severity in [
            ValidationSeverity.ERROR, ValidationSeverity.CRITICAL
        ]]
        assert len(error_results) == 0, f"不应该有严重错误: {error_results}"

    def test_real_world_scenario_daily_task(self, validator):
        """测试真实场景：日常任务"""
        agent_id = "athena"
        action = "data_analysis"  # 有效操作
        context = {
            "task": "分析用户行为数据",
            "resource_hours": 1.5
        }

        is_valid, results = validator.validate_decision(agent_id, action, context)

        # 应该有效
        assert is_valid
        error_results = [r for r in results if r.severity in [
            ValidationSeverity.ERROR, ValidationSeverity.CRITICAL
        ]]
        assert len(error_results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
