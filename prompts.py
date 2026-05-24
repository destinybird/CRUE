"""
Prompt Templates Module
所有LLM prompt模板集中管理
"""

# ==================== 临床背景合成 Prompt ====================
CLINICAL_SYNTHESIS_PROMPT = """你是一位资深的肺科医生，需要根据以下肺结节特征信息，生成3个不同但合理的患者临床背景。

## 肺结节特征
- 结节ID: {nodule_id}
- 位置: {location}
- 直径: {diameter_mm}mm
- 恶性程度评分: {malignancy_score}/5
- 毛刺征评分: {spiculation_score}/5
- 质地类型: {texture_type} (1=非实性, 2=部分实性, 3=实性)
- 亚实性评分: {subsolid_score}/5
- 分叶征评分: {lobulation_score}/5

## 约束条件
1. **年龄范围**: 35-80岁，恶性程度高时偏向50-75岁
2. **性别**: 随机，但需符合流行病学特征（男性略多）
3. **吸烟史**: 
   - 实性结节多见于吸烟者
   - 非实性结节多见于非吸烟女性
4. **症状**: 
   - 早期结节多为体检发现，无症状
   - 较大结节可能有咳嗽、胸痛等
5. **既往史**: 合理关联，如吸烟者可能有COPD
6. **家族史**: 恶性程度高时可有肿瘤家族史
7. **不能出现的数据**:
   - 年龄与症状严重程度严重不符
   - 非吸烟者有重度COPD
   - 无症状但已远处转移
   - 严重违反临床常识的组合

## 输出格式
请输出3个不同的患者，每个患者包含以下信息，使用JSON格式：

```json
[
  {{
    "patient_id": "P001",
    "age": 65,
    "gender": "男",
    "smoking_history": "40年吸烟史，每日20支",
    "smoking_pack_years": 40,
    "chief_complaint": "体检发现肺结节1周",
    "present_illness": "患者1周前单位体检行胸部CT发现右肺结节，无咳嗽、咳痰、胸痛、咯血等症状。",
    "past_history": "高血压病史10年，规律服药；否认糖尿病、冠心病史。",
    "family_history": "父亲有肺癌病史。",
    "physical_exam": "一般情况良好，心肺听诊未见明显异常。",
    "lab_tests": "血常规、肝肾功能正常，肿瘤标志物CEA、NSE、CYFRA21-1均在正常范围。",
    "clinical_phase": "screening",
    "has_symptoms": false,
    "ecog_ps": 1,
    "comorbidities": ["hypertension"],
    "surgical_risk": "low",
    "prior_cancer_history": false,
    "has_pet_scan": false,
    "pet_suv_max": null,
    "has_biopsy": false,
    "biopsy_result": null,
    "growth_rate_category": null,
    "is_growing": false,
    "is_new": true,
    "is_stable": false,
    "time_since_first_detection_months": 0,
    "patient_preference": "shared_decision",
    "cancer_type": null,
    "histology": null,
    "tnm_stage": null,
    "biomarkers": null
  }},
  // ... 另外2个患者
]
```

## 新增字段说明
1. **clinical_phase**: 必须为以下之一: "screening"(筛查发现), "incidental"(偶然发现), "surveillance"(随访中), "diagnostic"(诊断阶段), "treatment"(治疗阶段)
2. **has_symptoms**: 是否有症状（咳嗽、胸痛、咯血等）
3. **ecog_ps**: ECOG体力状态评分(0-4)，多数患者0-2
4. **comorbidities**: 合并症列表，如["hypertension", "copd", "diabetes"]等
5. **surgical_risk**: 手术风险 "low"/"moderate"/"high"，与年龄和合并症相关
6. **prior_cancer_history**: 是否有既往肿瘤病史
7. **has_pet_scan/pet_suv_max**: 是否做过PET-CT及SUV值。恶性程度高(≥4)的结节更可能已做PET
8. **has_biopsy/biopsy_result**: 是否做过活检及结果。仅诊断/治疗阶段可能有
9. **growth_rate_category**: 生长速度 "slow"/"moderate"/"rapid"/null。surveillance阶段才有
10. **is_growing/is_new/is_stable**: 结节动态变化。新发现时is_new=true；随访中根据情况设置
11. **time_since_first_detection_months**: 首次发现至今月数。新发现为0
12. **patient_preference**: 患者偏好 "aggressive"/"conservative"/"shared_decision"
13. **cancer_type/histology/tnm_stage/biomarkers**: 仅treatment阶段且已确诊时填写，否则null

## 场景多样性要求
- 3个患者应覆盖不同clinical_phase（如一个screening、一个surveillance、一个diagnostic）
- 恶性程度低(1-2)的结节：多为screening/incidental，无PET/活检
- 恶性程度中(3)的结节：可为surveillance，可能有PET
- 恶性程度高(4-5)的结节：可为diagnostic/treatment，可能有PET和活检
- 请确保3个患者在年龄、性别、吸烟史、临床阶段等方面有明显差异，但都与结节特征相匹配。"""

# ==================== 病历生成 Prompt ====================
RECORD_GENERATION_PROMPT = """你是一位资深的肺科医生，需要根据以下信息生成一份规范的住院病历。

## 患者信息
- 患者ID: {patient_id}
- 年龄: {age}岁
- 性别: {gender}
- 吸烟史: {smoking_history}
- 主诉: {chief_complaint}
- 现病史: {present_illness}
- 既往史: {past_history}
- 家族史: {family_history}
- 体格检查: {physical_exam}
- 辅助检查: {lab_tests}

## 结节特征
- 位置: {location}
- 直径: {diameter_mm}mm
- 大小分类: {size_category}
- 质地: {texture_desc}
- 恶性程度: {malignancy_desc}
- 毛刺征: {spiculation_desc}
- 分叶征: {lobulation_desc}
- 风险评估: {risk_assessment}

## EBM规则匹配结果
{matched_rules_text}

## 输出要求
1. 按照标准住院病历格式书写
2. 包含以下部分：
   - 【主诉】
   - 【现病史】
   - 【既往史】
   - 【个人史】
   - 【家族史】
   - 【体格检查】
   - 【辅助检查】
   - 【影像学检查】（重点描述CT特征）
   - 【初步诊断】
   - 【诊断依据】
   - 【鉴别诊断】
   - 【诊疗计划】（基于EBM规则）
3. 语言专业、规范，符合临床病历书写要求
4. 诊疗计划需引用匹配的EBM规则"""

# ==================== 对话生成 Prompt ====================
DIALOG_GENERATION_PROMPT = """你是一位资深的肺科医生，需要根据以下病历信息，生成一段医患对话。

## 病历信息
{medical_record_text}

## 患者背景
- 年龄: {age}岁
- 性别: {gender}
- 吸烟史: {smoking_history}

## EBM循证医学规则（医生必须在对话中体现以下管理建议）
- 风险等级: {risk_level}
- 管理建议摘要: {management_summary}
- 匹配的EBM规则:
{matched_rules_text}

## 对话要求
1. **对话轮次**: 5-8轮
2. **对话风格**: 
   - 医生：专业、耐心、有同理心
   - 患者：有疑虑、提问、需要解释
3. **对话内容应涵盖**:
   - 患者描述症状和担忧
   - 医生解释检查结果
   - 医生解释结节性质和风险
   - 患者提问关于治疗方案
   - 医生给出诊疗建议
   - 患者询问预后和随访
4. **语言要求**:
   - 医生语言专业但通俗易懂
   - 患者语言自然，带有情绪（担忧、疑惑、释然等）
   - 避免过于专业的术语堆砌
5. **不能出现**:
   - 医生给出确定性诊断（应为"考虑"、"可能"等）
   - 医生承诺治愈
   - 违反医疗规范的表述

## 输出格式
```json
[
  {{"role": "user", "content": "患者的第一句话"}},
  {{"role": "assistant", "content": "医生的回复"}},
  // ... 更多对话轮次
]
```"""

# ==================== 特征翻译 Prompt ====================
FEATURE_TRANSLATION_PROMPT = """你是一位医学影像专家，需要将LIDC-IDRI数据集中的数字特征翻译为临床描述。

## 输入特征
- malignancy: {malignancy} (1-5, 1=高度良性, 5=高度恶性)
- spiculation: {spiculation} (1-5, 1=无毛刺, 5=明显毛刺)
- texture: {texture} (1-5, 1=非实性, 5=实性)
- lobulation: {lobulation} (1-5, 1=光滑, 5=明显分叶)
- subtlety: {subtlety} (1-5, 1=非常明显, 5=非常细微)
- diameter_mm: {diameter_mm}

## 输出要求
请输出JSON格式的翻译结果：
```json
{{
  "malignancy_desc": "良性/可能良性/不确定/可能恶性/恶性",
  "spiculation_desc": "无毛刺/轻微毛刺/中等毛刺/明显毛刺/严重毛刺",
  "texture_desc": "纯磨玻璃/磨玻璃为主/混合密度/实性为主/完全实性",
  "lobulation_desc": "光滑/轻微分叶/中等分叶/明显分叶/严重分叶",
  "size_category": "微小结节(<5mm)/小结节(5-10mm)/中等结节(10-20mm)/大结节(20-30mm)/巨大结节(>30mm)",
  "risk_level": "低危/中危/高危（必须与CSV源数据risk_level字段保持一致）"
}}
```"""