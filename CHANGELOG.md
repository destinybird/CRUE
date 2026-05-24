# Changelog

## 2026-04-13: 131条EBM规则引擎改造

### 概述
将旧的 `RuleMatcher`（logistic概率模型）替换为基于循证医学的 `EBMEngine`，实现131条规则全覆盖。

### 新增文件 (data_pipeline/)
| 文件 | 说明 |
|------|------|
| `patient_state.py` | 94字段 dataclass，与 condition_registry 1:1 对齐 |
| `condition_registry.py` | 131个 `@register` 函数，`CONDITION_REGISTRY[name] = func(ps) → bool` |
| `ebm_engine.py` | 桥接模块，`generate_ebm_plan(features, patient) → plan dict`，含 `malignancy_risk / matched_rules / management_categories / risk_level / management_summary / matched_rules_text` |

### 修改文件
| 文件 | 改动 |
|------|------|
| `data_pipeline.py` | Step3 改 per-patient 循环（每 patient 独立匹配），management_plans 为 `List[plan]`，Step5 传 list |
| `main_pipeline.py` | import/init/process_nodule/SFT 全改用 EBMEngine；流程 = 合成临床 → `build_patient_state_dict` → EBM 匹配 → record + dialog |
| `clinical_synthesizer.py` | 新增 `build_patient_state_dict(features, patient) → PatientState dict` |
| `prompts.py` (code/) | 扩展 18+ PatientState 字段 + 场景多样性约束 |
| `__init__.py` | 导出 `EBMEngine / PatientState / CONDITION_REGISTRY` |

### 新流程
```
CSV行 → 提取nodule_features
     → clinical_synthesizer.synthesize() 生成多个patient
     → 每个patient: build_patient_state_dict → EBMEngine.generate_ebm_plan → plan
     → record_generator + dialog_generator 使用 plan 生成病历和对话
```

### 兼容性
- `record_generator.generate_batch` 改为接受 `List[Dict]`
- 旧 `rule_matcher.py` 保留（test 脚本兼容），main_pipeline 已无引用

### 已知坑点
- PS 字段名必须与 registry 中 `ps.xxx` 完全一致（曾因命名不匹配导致运行时报错）
- 文件名禁与同目录包名冲突（如 `rule_engine.py` vs `rule_engine/` → import 自引用死循环）
- NaN 穿透：`row.get(col, default)` 当列存在值 NaN 时返回 NaN，需用 `_safe_int/_safe_float` 检测 `pd.isna`