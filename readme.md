lung_agent/
│
├── README.md                          # 项目说明、快速开始、引用
├── LICENSE                            # 开源协议
├── requirements.txt                   # Python依赖
├── setup.py                           # 包安装配置
├── .gitignore                         # Git忽略文件
│
├── configs/                           # 配置文件目录
│   ├── lung_cot_lora.yaml            # SFT LoRA训练配置
│   ├── lung_cot_grpo.yaml            # GRPO强化训练配置
│   ├── data_config.yaml              # 数据构建配置
│   └── eval_config.yaml              # 评估配置
│
├── data/                              # 数据目录
│   ├── raw/                          # 原始数据（不入Git，用.gitignore）
│   │   ├── LIDC-IDRI/                # LIDC-IDRI原始数据
│   │   └── MSD_Lung/                 # MSD Lung数据
│   │
│   ├── ebm_rules/                    # EBM循证规则
│   │   ├── NSCLC_v3.xlsx             # NSCLC规则（68条）
│   │   ├── SCLC_v3.xlsx              # SCLC规则（62条）
│   │   └── rules_summary.md          # 规则说明文档
│   │
│   ├── processed/                    # 处理后的数据
│   │   ├── seed_cases.csv            # 种子病例（LIDC特征提取）
│   │   ├── matched_rules.json        # 规则匹配结果
│   │   ├── patient_profiles.json     # 合成患者信息
│   │   └── medical_records.json      # 生成的病历
│   │
│   └── sft/                          # SFT训练数据
│       ├── lung_cot_train.json       # 训练集
│       ├── lung_cot_val.json         # 验证集
│       └── lung_cot_test.json        # 测试集（预留5%）
│
├── src/                               # 源代码目录
│   ├── __init__.py
│   │
│   ├── data_pipeline/                # 数据构建Pipeline
│   │   ├── __init__.py
│   │   ├── lidc_extractor.py         # LIDC-IDRI特征提取（pylidc）
│   │   ├── msd_extractor.py          # MSD Lung肿瘤提取
│   │   ├── clinical_synthesizer.py   # 临床背景合成
│   │   ├── rule_matcher.py           # EBM规则匹配（三层策略）
│   │   ├── record_generator.py       # 病历文本生成
│   │   └── dialog_generator.py       # 多轮对话生成
│   │
│   ├── training/                     # 训练模块
│   │   ├── __init__.py
│   │   ├── sft_trainer.py            # SFT训练封装
│   │   ├── grpo_trainer.py           # GRPO强化训练
│   │   └── reward_functions.py       # 奖励函数（格式/EBM/质量）
│   │
│   ├── evaluation/                   # 评估模块
│   │   ├── __init__.py
│   │   ├── format_evaluator.py       # 格式完整率评估
│   │   ├── ebm_evaluator.py          # EBM对齐分数
│   │   ├── accuracy_evaluator.py     # 诊断准确率
│   │   └── human_eval.py             # 人工评估工具
│   │
│   └── utils/                        # 工具函数
│       ├── __init__.py
│       ├── ebm_parser.py             # EBM规则解析器
│       ├── feature_translator.py     # 数值→临床描述翻译
│       ├── prompt_templates.py       # Prompt模板
│       └── data_validator.py         # 数据质量校验
│
├── scripts/                           # 执行脚本
│   ├── 01_extract_lidc.sh            # 提取LIDC特征
│   ├── 02_extract_msd.sh             # 提取MSD特征
│   ├── 03_match_rules.sh             # 规则匹配
│   ├── 04_generate_dialogs.sh        # 生成对话
│   ├── 05_train_sft.sh               # SFT训练
│   ├── 06_train_grpo.sh              # GRPO训练
│   ├── 07_evaluate.sh                # 评估
│   └── run_full_pipeline.sh          # 一键运行全流程
│
├── notebooks/                         # Jupyter笔记本
│   ├── 01_data_exploration.ipynb     # 数据探索
│   ├── 02_rule_analysis.ipynb        # 规则分析
│   ├── 03_case_demo.ipynb            # 单病例演示
│   └── 04_results_visualization.ipynb # 结果可视化
│
├── models/                            # 模型目录（不入Git）
│   ├── base/                         # 基座模型（Qwen2.5-7B）
│   ├── sft_merged/                   # SFT后合并模型
│   └── grpo_final/                   # GRPO最终模型
│
├── outputs/                           # 输出目录（不入Git）
│   ├── logs/                         # 训练日志
│   ├── checkpoints/                  # 模型检查点
│   └── eval_results/                 # 评估结果
│
├── tests/                             # 单元测试
│   ├── test_rule_matcher.py
│   ├── test_dialog_generator.py
│   └── test_reward_functions.py
│
├── docs/                              # 文档
│   ├── data_pipeline.md              # 数据Pipeline说明
│   ├── training_guide.md             # 训练指南
│   ├── evaluation_guide.md           # 评估指南
│   └── api_reference.md              # API参考
│
└── examples/                          # 示例
    ├── example_single_case.py        # 单病例处理示例
    ├── example_batch_process.py      # 批量处理示例
    └── example_inference.py          # 推理示例



# Lung Agent: 肺部临床推理AI助手

基于EBM规则驱动的长思维链肺部诊疗推理模型（7B参数）

## 🎯 核心特性
- LIDC-IDRI + MSD Lung 数据驱动
- 131条EBM循证规则对齐（NSCLC 68条 + SCLC 62条）
- SFT + GRPO两阶段训练
- 长思维链推理（影像→病理→鉴别→诊断→建议）

## 📊 数据构建流程
1. LIDC-IDRI特征提取 → 结节结构化数据
2. EBM规则匹配 → 三层匹配策略
3. 临床背景合成 → 流行病学一致
4. 多轮对话生成 → SFT训练数据

## 🚀 快速开始
...

## 📚 引用
...



1. 终端详细打印
每个结节处理完后会打印：

============================================================
【结节 12345 生成结果】
============================================================

📊 风险评估:
  风险等级: 中
  恶性概率: 45%

📋 管理计划:
  建议6个月后复查CT...

🏥 临床背景:
  患者，男，58岁，吸烟史...

📝 生成病历:
----------------------------------------
[病历内容]
----------------------------------------

💬 医患对话:
----------------------------------------
[医生]: ...
[患者]: ...
----------------------------------------
2. 实时保存
每处理完一个结节立即保存，不用担心中途断掉丢失数据：

文件	格式	说明
realtime_results.json	JSON	完整结果（实时追加）
realtime_sft.jsonl	JSONL	SFT训练格式（实时追加）
final_results.json	JSON	最终完整结果
运行方式
cd /Users/yixuanli/Downloads/LUNG_papers/code

# 处理3个结节
python main_pipeline.py --lidc_csv data/raw/lidc_nodule_features.csv --n_samples 3 --output_dir output

# 处理特定恶性等级的结节
python main_pipeline.py --lidc_csv data/raw/lidc_nodule_features.csv --by_malignancy 4 --n_samples 5
注意：请先将代码中的 DEEPSEEK_API_KEY 替换为你的实际密钥。




realtime_results.json 数据结构文档
文件概述
realtime_results.json 是肺结节数据合成管道的实时输出文件，包含从 LIDC 数据集特征到完整临床数据的转换结果。

数据结构
{
  "nodule_id_1": {
    "nodule_features": {...},
    "clinical_context": [...],
    "risk_assessment": {...},
    "management_plan": {...},
    "medical_record": {...},
    "dialog": {...}
  },
  "nodule_id_2": {...}
}
1. nodule_features - 结节特征
定义: 从 LIDC 数据集提取的肺结节影像学特征

获取方式: LIDCExtractor.extract_features() 从 CSV 文件读取

数据来源: data/raw/lidc_nodule_features.csv

字段说明:

字段	类型	说明
nodule_id	string	结节唯一标识符
location	string	结节位置（如"右肺上叶"）
diameter_mm	float	结节直径（毫米）
texture	int	质地类型：1=纯磨玻璃，2=部分实性，3=实性
malignancy	int	恶性评分：1-5（高度良性→高度恶性）
spiculation	int	毛刺征评分：1-5
lobulation	int	分叶征评分：1-5
subsolid	int	亚实性评分：1-5
calcification	int	钙化评分：1-6
sphericity	int	球形度评分：1-5
2. clinical_context - 临床背景
定义: 根据结节特征生成的 3 个不同患者临床背景

获取方式: ClinicalSynthesizer.synthesize() 调用 LLM 生成

数据来源: 基于 nodule_features 通过 GPT 生成

字段说明 (每个患者对象):

字段	类型	说明
patient_id	string	患者唯一标识符
age	int	年龄（35-80岁）
gender	string	性别（男/女）
smoking_history	string	吸烟史
chief_complaint	string	主诉
present_illness	string	现病史
past_history	string	既往史
family_history	string	家族史
physical_exam	string	体格检查
lab_tests	string	实验室检查
3. risk_assessment - 风险评估
定义: 基于结节特征的恶性风险评估

获取方式: RuleMatcher.assess_malignancy_risk() 基于规则计算

数据来源: 基于 nodule_features 通过规则引擎计算

字段说明:

字段	类型	说明
malignancy_score	int	原始恶性评分（1-5）
risk_level	string	风险等级：极低/低/中等/高/极高
probability	string	恶性概率范围（如"5-65%"）
recommended_action	string	建议行动
risk_factors	list	风险因素列表（如"毛刺征阳性"）
protective_factors	list	保护因素列表（如"钙化存在"）
4. management_plan - 管理计划
定义: 基于 Fleischner 指南的随访管理建议

获取方式: RuleMatcher.generate_management_plan() 生成

数据来源: 基于 nodule_features 匹配临床指南规则

字段说明:

字段	类型	说明
nodule_id	string	结节ID
fleischner_rule	object	Fleischner指南匹配结果
fleischner_rule.rule_name	string	规则名称
fleischner_rule.description	string	规则描述
fleischner_rule.recommendation	string	随访建议
fleischner_rule.follow_up_months	int	随访间隔（月）
malignancy_risk	object	恶性风险评估（同risk_assessment）
management_summary	string	管理计划摘要文本
5. medical_record - 病历文本
定义: 生成的完整病历文书

获取方式: RecordGenerator.generate() 调用 LLM 生成

数据来源: 基于 clinical_context[0] + nodule_features + risk_assessment 生成

字段说明:

字段	类型	说明
patient_id	string	患者ID
nodule_id	string	结节ID
full_text	string	完整病历文本
patient_info	object	患者信息（来自clinical_context）
nodule_features	object	结节特征（来自nodule_features）
6. dialog - 医患对话
定义: 基于病历生成的多轮医患对话

获取方式: DialogGenerator.generate() 调用 LLM 生成

数据来源: 基于 medical_record 生成

字段说明:

字段	类型	说明
patient_id	string	患者ID
nodule_id	string	结节ID
raw_text	string	原始对话文本
turns	list	结构化对话轮次列表
turns[].role	string	角色：doctor/patient
turns[].content	string	对话内容
num_turns	int	对话轮数
