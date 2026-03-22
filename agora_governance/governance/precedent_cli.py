"""
先例管理 CLI 工具

版本: v1.0
创建日期: 2026-03-20
作者: Code 💻
状态: Phase 2 开发中

功能:
- 导入历史决策
- 标记先例
- 设置权重
- 查询统计
"""

import json
import sys
from pathlib import Path
from agora.governance.precedent_db import PrecedentDatabase, Precedent, calculate_precedent_weight


def import_decision_log(db_path: str = "agora/governance/decisions.jsonl"):
    """
    导入历史决策日志到先例数据库

    Args:
        db_path: 决策日志文件路径
    """
    db = PrecedentDatabase()

    if not Path(db_path).exists():
        print(f"❌ 决策日志文件不存在: {db_path}")
        return

    # 读取决策日志
    imported = 0
    with open(db_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)

                    # 转换为先例对象
                    precedent = Precedent(
                        decision_id=data.get("decision_id", ""),
                        timestamp=data.get("timestamp", ""),
                        task_id=data.get("task_id", "unknown"),
                        description=data.get("description", ""),
                        approved=data.get("approved", False),
                        stage=data.get("stage", ""),
                        reasoning=data.get("reasoning", ""),
                        local_reviews=data.get("local_reviews", {}),
                        global_votes=data.get("global_votes"),
                        tmind_decision=data.get("tmind_decision"),
                        precedent=False,  # 默认不标记为先例
                        precedent_weight=0.0,
                        citation_count=0,
                        tags=[],
                        category=""
                    )

                    # 检查是否已存在
                    if not db.get_by_id(precedent.decision_id):
                        db.add(precedent)
                        imported += 1

                except Exception as e:
                    print(f"⚠️ 导入失败: {e}")

    print(f"✅ 导入完成: {imported} 条决策")
    print(f"📊 当前数据库: {db.get_stats()}")


def list_precedents(limit: int = 20):
    """
    列出所有先例

    Args:
        limit: 显示数量限制
    """
    db = PrecedentDatabase()

    if not db.precedents:
        print("📭 数据库为空")
        return

    # 按权重排序
    sorted_precedents = sorted(
        db.precedents,
        key=lambda p: p.precedent_weight,
        reverse=True
    )

    print(f"\n📚 先例列表（Top {min(limit, len(sorted_precedents))}）\n")

    for i, p in enumerate(sorted_precedents[:limit], 1):
        marker = "⭐" if p.precedent_weight >= 5.0 else "📖" if p.precedent else "📄"
        print(f"{i}. {marker} {p.decision_id}")
        print(f"   任务: {p.description[:50]}...")
        print(f"   结果: {'✅ 批准' if p.approved else '❌ 拒绝'}")
        print(f"   权重: {p.precedent_weight:.1f}/5.0")
        print(f"   引用: {p.citation_count} 次")
        print()


def mark_precedent(decision_id: str, weight: float = 1.0):
    """
    标记决策为先例

    Args:
        decision_id: 决策 ID
        weight: 初始权重（0-5）
    """
    db = PrecedentDatabase()
    precedent = db.get_by_id(decision_id)

    if not precedent:
        print(f"❌ 决策不存在: {decision_id}")
        return

    db.mark_as_precedent(decision_id, weight)
    print(f"✅ 已标记为先例: {decision_id}")
    print(f"   权重: {weight:.1f}/5.0")


def set_weight(decision_id: str, weight: float):
    """
    设置先例权重

    Args:
        decision_id: 决策 ID
        weight: 新权重（0-5）
    """
    db = PrecedentDatabase()
    precedent = db.get_by_id(decision_id)

    if not precedent:
        print(f"❌ 决策不存在: {decision_id}")
        return

    db.update_weight(decision_id, weight)
    marker = "⭐ 超级先例" if weight >= 5.0 else "📖 先例"
    print(f"✅ 权重已更新: {decision_id}")
    print(f"   {marker}: {weight:.1f}/5.0")


def search_precedents(query: str, threshold: float = 0.3, top_k: int = 5):
    """
    搜索先例

    Args:
        query: 查询文本
        threshold: 相似度阈值
        top_k: 返回数量
    """
    db = PrecedentDatabase()
    results = db.search(query, threshold, top_k)

    if not results:
        print(f"🔍 未找到相关先例: {query}")
        return

    print(f"\n🔍 搜索结果: {query}\n")

    for i, result in enumerate(results, 1):
        p = result["precedent"]
        sim = result["similarity"]
        weight = result["weight"]

        marker = "⭐" if weight >= 5.0 else "📖" if p.precedent else "📄"
        print(f"{i}. {marker} {p.decision_id}")
        print(f"   相似度: {sim:.2%}")
        print(f"   权重: {weight:.1f}/5.0")
        print(f"   描述: {p.description[:80]}...")
        print()


def show_stats():
    """显示数据库统计信息"""
    db = PrecedentDatabase()
    stats = db.get_stats()

    print("\n📊 先例数据库统计\n")
    print(f"总决策数: {stats['total_precedents']}")
    print(f"已标记先例: {stats['marked_precedents']}")
    print(f"超级先例: {stats['super_precedents']}")
    print(f"平均权重: {stats['avg_weight']:.2f}/5.0")
    print()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python precedent_cli.py import [decision_log_path]")
        print("  python precedent_cli.py list [limit]")
        print("  python precedent_cli.py mark <decision_id> [weight]")
        print("  python precedent_cli.py weight <decision_id> <weight>")
        print("  python precedent_cli.py search <query> [threshold] [top_k]")
        print("  python precedent_cli.py stats")
        return

    command = sys.argv[1]

    if command == "import":
        db_path = sys.argv[2] if len(sys.argv) > 2 else "agora/governance/decisions.jsonl"
        import_decision_log(db_path)

    elif command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        list_precedents(limit)

    elif command == "mark":
        if len(sys.argv) < 3:
            print("❌ 缺少参数: decision_id")
            return
        decision_id = sys.argv[2]
        weight = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        mark_precedent(decision_id, weight)

    elif command == "weight":
        if len(sys.argv) < 4:
            print("❌ 缺少参数: decision_id weight")
            return
        decision_id = sys.argv[2]
        weight = float(sys.argv[3])
        set_weight(decision_id, weight)

    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ 缺少参数: query")
            return
        query = sys.argv[2]
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
        top_k = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        search_precedents(query, threshold, top_k)

    elif command == "stats":
        show_stats()

    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
