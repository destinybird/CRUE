# CURE：基于循证医学规则增强的肺结节临床推理系统

CURE（Clinical reasoning system with evidence‑based medicine rUle enháncement）是一个面向肺结节辅助诊断的小型大语言模型系统。  
它以 Qwen2.5‑7B‑Instruct 为基座，通过监督微调 + 强化学习两阶段训练，并在推理阶段显式注入 **131 条循证医学规则**（Fleischner 指南、NCCN 指南等），实现了：

- 结构化病历生成（单轮）
- 多轮医患对话推理（含思维链）

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `infer_single_turn.py` | 单轮病历生成推理脚本。输入患者影像特征，输出结构化病历（影像学所见、临床分析、诊断意见、处置建议）。 |
| `eval_single_turn.py` | 单轮病历生成评估脚本。计算 ROUGE‑L、Rule Recall/Precision/F1 等指标，对比模型输出与参考答案。 |
| `infer_multi_turn.py` | 多轮医患对话推理脚本。支持 8‑15 轮交互，医生回复中嵌入 `<think>` 思维链，模拟真实门诊流程。 |
| `eval_multi_turn.py` | 多轮对话评估脚本。逐轮评估文本质量、规则遵循一致性，并计算跨轮次逻辑一致性指标。 |

> 已经产出的数据均存放于 `results/` 文件夹中。

---

## 免责声明

本系统及所有相关代码、模型、数据仅供学术研究和教学用途，不构成任何医疗建议、诊断或治疗方案。
在实际临床场景中使用本系统的输出，必须由具备执业资质的医师进行审慎判断并负全部责任。作者及项目参与方不对因使用本系统而产生的任何直接或间接后果承担法律责任。

---

## 仓库结构

| 路径 | 内容 |
|------|------|
| `data/raw/lidc_nodule_features.csv` | LIDC-IDRI 结构化标注表，7,048 行 × 13 字段 |
| `data/processed/lidc_filtered_balanced.csv` | 清洗后建模数据，2,424 行 × 19 字段 |
| `data/processed/filtering_report.txt` | 清洗各步骤的计数与分布 |
| `data/rules/ebm.xlsx` | 131 条循证医学规则（IF / THEN / Variable） |
| `data_pipeline/` | 数据构建流水线：特征提取、规则匹配、病历与对话生成 |
| `main_pipeline.py` | 单结节全流程入口 |
| `scripts/0_validate_quality.py` | 六维硬约束质检 |
| `eval_single_turn.py` / `eval_multi_turn.py` | 单轮 / 多轮评测 |
| `infer_single_turn.py` / `infer_multi_turn.py` | 单轮 / 多轮推理 |
| `results/` | 8 个模型 × 2 个场景的评测指标 |
| `docs/数据预处理说明.md` | 数据来源、清洗规则、质检判据与全部统计数字 |
| `docs/数据流转图.png` | 从原始标注到训练集的一图流 |

## 数据规模

```
LIDC-IDRI 原始标注      7,048 条
  -> 字段完整性校验      7,032 条
  -> 多标注者共识去重    6,389 个结节
  -> 数值组合去重        3,816 条
  -> 恶性度分层配平      2,424 个结节
  -> 一对三语料生成      7,272 条
  -> 六维硬约束质检      6,981 / 5,854 条（单轮 / 多轮）
  -> 大模型语义审核      6,546 / 4,566 条
  -> 最终训练语料        7,269 条
```

评测集：429 个结节 → 722 条洁净样本 → 单轮 722 / 多轮 4,411 个评测轮次。
