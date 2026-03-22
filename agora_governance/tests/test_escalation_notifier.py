#!/usr/bin/env python3
"""
升级通知机制测试
版本: v1.0.0
测试覆盖率目标: ≥90%

作者: 忒弥斯 (T-Mind)
日期: 2026-03-17
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from escalation_notifier import EscalationNotifier, EscalationRecord
from conflict_resolver import ConflictResolver


class TestEscalationNotifier:
    """升级通知器测试"""

    @pytest.fixture
    def escalation_notifier(self):
        """创建升级通知器实例（禁用邮件）"""
        conflict_resolver = ConflictResolver()
        email_config = {
            "enabled": False  # 禁用邮件发送
        }
        return EscalationNotifier(conflict_resolver, email_config)

    def test_should_escalate_p0_error(self, escalation_notifier):
        """测试 P0 冲突解决失败需要升级"""
        resolution = {
            "resolution": "error",
            "reason": "无法自动解决"
        }

        should_escalate = escalation_notifier.should_escalate(resolution, "P0")

        assert should_escalate is True

    def test_should_escalate_p0_veto_without_override(self, escalation_notifier):
        """测试 P0 Crit 否决且无法推翻需要升级"""
        resolution = {
            "resolution": "veto",
            "reason": "Crit 行使否决权",
            "override_plan": None
        }

        should_escalate = escalation_notifier.should_escalate(resolution, "P0")

        assert should_escalate is True

    def test_should_not_escalate_p0_veto_with_override(self, escalation_notifier):
        """测试 P0 Crit 否决但有推翻方案不需要升级"""
        resolution = {
            "resolution": "veto",
            "reason": "Crit 行使否决权",
            "override_plan": "忒弥斯提供实测数据推翻"
        }

        should_escalate = escalation_notifier.should_escalate(resolution, "P0")

        assert should_escalate is False

    def test_should_not_escalate_p1(self, escalation_notifier):
        """测试 P1 冲突不需要升级"""
        resolution = {
            "resolution": "negotiate",
            "reason": "Agent 自行协商"
        }

        should_escalate = escalation_notifier.should_escalate(resolution, "P1")

        assert should_escalate is False

    def test_should_not_escalate_p2(self, escalation_notifier):
        """测试 P2 冲突不需要升级"""
        resolution = {
            "resolution": "coordinate",
            "reason": "忒弥斯协调"
        }

        should_escalate = escalation_notifier.should_escalate(resolution, "P2")

        assert should_escalate is False

    def test_escalate_to_human(self, escalation_notifier):
        """测试升级到哥哥"""
        conflict_level = "P0"
        agents = ["themis", "crit"]
        description = "架构方向分歧"
        resolution_attempt = {
            "resolution": "error",
            "reason": "无法达成一致"
        }
        context = {
            "security_risk": True
        }

        record = escalation_notifier.escalate_to_human(
            conflict_level=conflict_level,
            agents=agents,
            description=description,
            resolution_attempt=resolution_attempt,
            context=context
        )

        # 验证记录
        assert record.escalation_id.startswith("esc_")
        assert record.conflict_level == "P0"
        assert record.agents == agents
        assert record.description == description
        assert record.resolution_attempt == "error"
        assert record.failure_reason == "无法达成一致"
        assert record.status == "notified"

    def test_save_escalation_record(self, escalation_notifier, tmp_path):
        """测试保存升级记录"""
        # 修改保存路径到临时目录
        escalation_notifier.escalation_dir = tmp_path

        record = EscalationRecord(
            escalation_id="esc_test",
            timestamp=datetime.now().isoformat(),
            conflict_level="P0",
            agents=["themis", "crit"],
            description="测试冲突",
            resolution_attempt="error",
            failure_reason="测试原因",
            context={},
            status="pending"
        )

        escalation_notifier._save_escalation_record(record)

        # 验证文件已创建
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = tmp_path / f"escalations_{date_str}.json"
        assert file_path.exists()

        # 验证内容
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)

        assert len(records) == 1
        assert records[0]["escalation_id"] == "esc_test"

    def test_get_pending_escalations(self, escalation_notifier, tmp_path):
        """测试获取待处理的升级记录"""
        # 修改保存路径到临时目录
        escalation_notifier.escalation_dir = tmp_path

        # 创建测试记录
        record1 = EscalationRecord(
            escalation_id="esc_test1",
            timestamp=datetime.now().isoformat(),
            conflict_level="P0",
            agents=["themis"],
            description="测试冲突1",
            resolution_attempt="error",
            failure_reason="测试",
            context={},
            status="pending"
        )

        record2 = EscalationRecord(
            escalation_id="esc_test2",
            timestamp=datetime.now().isoformat(),
            conflict_level="P0",
            agents=["crit"],
            description="测试冲突2",
            resolution_attempt="error",
            failure_reason="测试",
            context={},
            status="resolved"  # 已解决
        )

        escalation_notifier._save_escalation_record(record1)
        escalation_notifier._save_escalation_record(record2)

        # 获取待处理记录
        pending = escalation_notifier.get_pending_escalations()

        # 应该只有 1 条（record2 已解决）
        assert len(pending) == 1
        assert pending[0].escalation_id == "esc_test1"

    def test_mark_resolved(self, escalation_notifier, tmp_path):
        """测试标记升级为已解决"""
        # 修改保存路径到临时目录
        escalation_notifier.escalation_dir = tmp_path

        # 创建测试记录
        record = EscalationRecord(
            escalation_id="esc_test",
            timestamp=datetime.now().isoformat(),
            conflict_level="P0",
            agents=["themis"],
            description="测试冲突",
            resolution_attempt="error",
            failure_reason="测试",
            context={},
            status="notified"
        )

        escalation_notifier._save_escalation_record(record)

        # 标记为已解决
        escalation_notifier.mark_resolved("esc_test", "哥哥决定：暂缓实施")

        # 验证状态已更新
        pending = escalation_notifier.get_pending_escalations()
        assert len(pending) == 0  # 应该没有待处理的了


class TestEscalationNotifierIntegration:
    """集成测试"""

    @pytest.fixture
    def escalation_notifier(self):
        """创建升级通知器实例（禁用邮件）"""
        conflict_resolver = ConflictResolver()
        email_config = {
            "enabled": False
        }
        return EscalationNotifier(conflict_resolver, email_config)

    def test_real_world_scenario_p0_conflict(self, escalation_notifier, tmp_path):
        """测试真实场景：P0 冲突升级"""
        # 修改保存路径到临时目录
        escalation_notifier.escalation_dir = tmp_path

        # 模拟 P0 冲突
        level = "P0"
        agents = ["themis", "shield"]
        description = "安全漏洞修复方案分歧"
        context = {
            "security_risk": True,
            "affects_stability": True
        }

        # 尝试解决（会失败）
        resolution = escalation_notifier.conflict_resolver.resolve_conflict(
            level=level,
            agents=agents,
            description=description,
            context=context
        )

        # 判断需要升级
        should_escalate = escalation_notifier.should_escalate(resolution, level)
        assert should_escalate is True

        # 执行升级
        record = escalation_notifier.escalate_to_human(
            conflict_level=level,
            agents=agents,
            description=description,
            resolution_attempt=resolution,
            context=context
        )

        # 验证
        assert record.conflict_level == "P0"
        assert record.status == "notified"

        # 验证文件已创建
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = tmp_path / f"escalations_{date_str}.json"
        assert file_path.exists()

    def test_format_email_body(self, escalation_notifier):
        """测试邮件内容格式化"""
        record = EscalationRecord(
            escalation_id="esc_test_20260317",
            timestamp="2026-03-17T19:00:00",
            conflict_level="P0",
            agents=["themis", "crit"],
            description="架构方向分歧",
            resolution_attempt="error",
            failure_reason="无法达成一致",
            context={"security_risk": True},
            status="pending"
        )

        body = escalation_notifier._format_email_body(record)

        # 验证关键内容
        assert "esc_test_20260317" in body
        assert "P0" in body
        assert "架构方向分歧" in body
        assert "themis" in body
        assert "crit" in body
        assert "无法达成一致" in body
        assert "<!DOCTYPE html>" in body or "<html>" in body


class TestEscalateIfNeeded:
    """便捷函数测试"""

    @pytest.fixture
    def components(self):
        """创建测试组件"""
        conflict_resolver = ConflictResolver()
        email_config = {"enabled": False}
        escalation_notifier = EscalationNotifier(conflict_resolver, email_config)
        return conflict_resolver, escalation_notifier

    def test_escalate_if_needed_p0_error(self, components, tmp_path):
        """测试 P0 错误时自动升级"""
        conflict_resolver, escalation_notifier = components
        escalation_notifier.escalation_dir = tmp_path

        from escalation_notifier import escalate_if_needed

        record = escalate_if_needed(
            conflict_resolver=conflict_resolver,
            escalation_notifier=escalation_notifier,
            level="P0",
            agents=["themis", "crit"],
            description="测试冲突",
            context={"invalid": "data"}  # 触发错误
        )

        # 应该升级了
        assert record is not None
        assert record.conflict_level == "P0"

    def test_escalate_if_needed_p1_no_escalate(self, components):
        """测试 P1 不需要升级"""
        conflict_resolver, escalation_notifier = components

        from escalation_notifier import escalate_if_needed

        record = escalate_if_needed(
            conflict_resolver=conflict_resolver,
            escalation_notifier=escalation_notifier,
            level="P1",
            agents=["athena", "aria"],
            description="任务优先级分歧",
            context={}
        )

        # 不应该升级
        assert record is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
