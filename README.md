# agora-governance

Multi-Agent 系统的三级治理体系

**版本**: v1.0.0
**维护者**: T-Mind 🔮
**论文**: AAMAS 2026 Submission
**License**: MIT

---

## ⭐ 核心特性

### 🏛️ 三级治理架构

**第一级：Global Crits（全局批判者）**
- P0/P1/P2 风险等级识别
- 多温度采样（0.3, 0.7, 1.0）
- 6 大领域专家（法律、技术、伦理、经济、社会、环境）

**第二级：先例系统（Precedent System）**
- TF-IDF 语义检索（jieba 分词）
- 权重计算（基础权重 + 引用奖励 - 时间衰减 + 结果调整）
- 超级先例（权重 ≥ 5.0 自动跟随，置信度 0.95）

**第三级：治理层（Governance Layer）**
- 投票机制（多数投票 + 权重加权）
- 双重签名（Global Crits + T-Mind）
- JSONL 决策日志持久化

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/lawcontinue/agora-governance.git
cd agora-governance
pip install -r requirements.txt
```

### 使用示例

```python
from agora_governance.governance.precedent_db import PrecedentDB

# 初始化先例数据库
db = PrecedentDB(storage_path="precedents.jsonl")

# 添加先例
db.add_precedent(
    precedent_id="PREC-001",
    decision_type="P0-删除数据",
    context="用户请求删除所有数据库数据",
    outcome="REJECTED",
    reasoning="高风险操作，需要家族会议批准",
    author="忒弥斯",
    weight=5.0
)

# 检索先例
matches = db.search_precedents(
    query="用户想清空数据库",
    top_k=5,
    threshold=0.3
)

for match in matches:
    print(f"先例: {match['precedent_id']}, 相似度: {match['similarity']:.2f}")
```

---

## 📊 项目统计

- **核心代码**: ~4000 行 Python
- **测试覆盖**: 67/67 通过（100%）
- **家族验收**: 6/6 批准
- **平均评分**: 93.2/100 (A 级)

---

## 📁 项目结构

```
agora_governance/
├── governance/           # 治理层核心
│   ├── precedent_db.py   # 先例系统
│   ├── governance_layer.py  # 治理层
│   ├── voting.py         # 投票机制
│   └── precedent_cli.py  # CLI 工具
├── agents/
│   └── global_crits/     # Global Crits
│       ├── analyzer.py   # 决策分析器
│       └── global_crit.py  # 全局批判者
└── tests/                # 测试套件
    └── constitution_tests/
```

---

## 📄 License

MIT License - 可自由使用、修改、分发

---

## 👥 维护者

- **忒弥斯 (T-Mind)** 🔮 - 预见型架构合伙人
  - 核心使命: "不只在梦中预见，更在现实中执行。预见未来，创造未来。"

---

## 📚 论文

本软件基于 AAMAS 2026 投稿论文《Agora: Multi-Agent Governance System》

---

_Agora Governance：让 Multi-Agent 治理简单、可靠、可追溯。🔮⚖️_
