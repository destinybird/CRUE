"""
condition_registry — 131条EBM规则的条件函数注册表
每个条件函数签名: (PatientState) -> bool
"""

from __future__ import annotations
from typing import Callable, Dict
try:
    from .patient_state import PatientState
except ImportError:
    from patient_state import PatientState

# 类型别名
ConditionFn = Callable[[PatientState], bool]

# ═══════════════════════════════════════════════════════════════
# 条件注册表: rule_id -> condition_function
# ═══════════════════════════════════════════════════════════════
CONDITION_REGISTRY: Dict[str, ConditionFn] = {}


def register(rule_id: str):
    """装饰器: 将条件函数注册到 CONDITION_REGISTRY"""
    def decorator(fn: ConditionFn) -> ConditionFn:
        CONDITION_REGISTRY[rule_id] = fn
        return fn
    return decorator


# ─── R-NODULE: 肺结节管理 (13条) ────────────────────────────

@register("R-NODULE-01")
def _(ps: PatientState) -> bool:
    """单发实性结节 <6mm, 低风险"""
    return (ps.nodule_count == 1 and ps.density == "solid"
            and ps.diameter_mm < 6 and ps.risk_level == "low")

@register("R-NODULE-02")
def _(ps: PatientState) -> bool:
    """单发实性结节 6-8mm, 低风险"""
    return (ps.nodule_count == 1 and ps.density == "solid"
            and 6 <= ps.diameter_mm <= 8 and ps.risk_level == "low")

@register("R-NODULE-03")
def _(ps: PatientState) -> bool:
    """单发实性结节 >8mm"""
    return (ps.nodule_count == 1 and ps.density == "solid"
            and ps.diameter_mm > 8)

@register("R-NODULE-04")
def _(ps: PatientState) -> bool:
    """单发实性结节 <6mm, 高风险"""
    return (ps.nodule_count == 1 and ps.density == "solid"
            and ps.diameter_mm < 6 and ps.risk_level == "high")

@register("R-NODULE-05")
def _(ps: PatientState) -> bool:
    """单发实性结节 6-8mm, 高风险"""
    return (ps.nodule_count == 1 and ps.density == "solid"
            and 6 <= ps.diameter_mm <= 8 and ps.risk_level == "high")

@register("R-NODULE-06")
def _(ps: PatientState) -> bool:
    """单发非实性结节 <6mm"""
    return (ps.nodule_count == 1 and ps.density == "ground_glass"
            and ps.diameter_mm < 6)

@register("R-NODULE-07")
def _(ps: PatientState) -> bool:
    """单发非实性结节 >=6mm"""
    return (ps.nodule_count == 1 and ps.density == "ground_glass"
            and ps.diameter_mm >= 6)

@register("R-NODULE-08")
def _(ps: PatientState) -> bool:
    """单发部分实性结节 >=6mm"""
    return (ps.nodule_count == 1 and ps.density == "part_solid"
            and ps.diameter_mm >= 6 and ps.solid_component_mm < 6)

@register("R-NODULE-09")
def _(ps: PatientState) -> bool:
    """单发部分实性结节 >=6mm, 实性成分>=6mm"""
    return (ps.nodule_count == 1 and ps.density == "part_solid"
            and ps.diameter_mm >= 6 and ps.solid_component_mm >= 6)

@register("R-NODULE-10")
def _(ps: PatientState) -> bool:
    """多发非实性/部分实性结节, 均<6mm"""
    return (ps.nodule_count >= 2
            and ps.density in ("ground_glass", "part_solid")
            and ps.diameter_mm < 6)

@register("R-NODULE-11")
def _(ps: PatientState) -> bool:
    """多发非实性/部分实性结节, 至少1个>=6mm"""
    return (ps.nodule_count >= 2
            and ps.density in ("ground_glass", "part_solid")
            and ps.diameter_mm >= 6)

@register("R-NODULE-12")
def _(ps: PatientState) -> bool:
    """结节不可手术切除"""
    return not ps.surgery_eligible or not ps.resectable

@register("R-NODULE-13")
def _(ps: PatientState) -> bool:
    """计划SABR或术前全身治疗"""
    return ps.planned_treatment in ("sabr", "neoadjuvant")


# ─── R-EXAM: 检查评估 (NSCLC, 13条) ────────────────────────

@register("R-EXAM-01")
def _(ps: PatientState) -> bool:
    """初始就诊, 未完成NSCLC基础评估"""
    return (ps.clinical_phase == "initial_workup"
            and ps.cancer_type == "nsclc"
            and not ps.basic_assessment_done)

@register("R-EXAM-02")
def _(ps: PatientState) -> bool:
    """初始就诊, 未完成基础实验室检查"""
    return (ps.clinical_phase == "initial_workup"
            and ps.cancer_type == "nsclc"
            and not ps.lab_tests_done)

@register("R-EXAM-03")
def _(ps: PatientState) -> bool:
    """NSCLC初始分期, 胸部造影CT未完成"""
    return (ps.clinical_phase in ("initial_workup", "staging")
            and ps.cancer_type == "nsclc"
            and not ps.chest_ct_done)

@register("R-EXAM-03-B")
def _(ps: PatientState) -> bool:
    """NSCLC治疗决策, 最近分期扫描超过60天"""
    return (ps.clinical_phase in ("staging", "treatment")
            and ps.cancer_type == "nsclc"
            and ps.chest_ct_done and ps.chest_ct_days_ago > 60)

@register("R-EXAM-04")
def _(ps: PatientState) -> bool:
    """NSCLC初始分期, FDG PET/CT未完成"""
    return (ps.clinical_phase in ("initial_workup", "staging")
            and ps.cancer_type == "nsclc"
            and not ps.pet_ct_done)

@register("R-EXAM-05-A")
def _(ps: PatientState) -> bool:
    """NSCLC初始分期, 怀疑脑转移, MRI可行"""
    return (ps.clinical_phase in ("initial_workup", "staging")
            and ps.cancer_type == "nsclc"
            and ps.brain_metastasis and ps.mri_feasible)

@register("R-EXAM-05-B")
def _(ps: PatientState) -> bool:
    """NSCLC初始分期, 怀疑脑转移, MRI不可行"""
    return (ps.clinical_phase in ("initial_workup", "staging")
            and ps.cancer_type == "nsclc"
            and ps.brain_metastasis and not ps.mri_feasible)

@register("R-EXAM-06")
def _(ps: PatientState) -> bool:
    """肺上沟肿瘤"""
    return ps.pancoast_tumor

@register("R-EXAM-07")
def _(ps: PatientState) -> bool:
    """计划手术, 支气管镜未完成"""
    return (ps.planned_treatment == "surgery"
            and not ps.bronchoscopy_done)

@register("R-EXAM-08")
def _(ps: PatientState) -> bool:
    """需要肺功能评估, 未完成（仅确诊后适用）"""
    return (ps.cancer_type == "nsclc"
            and ps.clinical_phase != "screening"
            and not ps.pft_done)

@register("R-EXAM-09")
def _(ps: PatientState) -> bool:
    """肿瘤大且靠近纵隔, 或早期/局部晚期需纵隔分期"""
    return (ps.tumor_near_mediastinum or ps.mediastinal_staging_needed)

@register("R-EXAM-10")
def _(ps: PatientState) -> bool:
    """肿瘤非常小, 位于与纵隔相反侧"""
    return ps.tumor_very_small and ps.tumor_opposite_mediastinum

@register("R-EXAM-11")
def _(ps: PatientState) -> bool:
    """计划手术, 肿瘤非very small"""
    return (ps.planned_treatment == "surgery"
            and not ps.tumor_very_small)

@register("R-EXAM-12")
def _(ps: PatientState) -> bool:
    """计划手术, 肿瘤very small"""
    return (ps.planned_treatment == "surgery"
            and ps.tumor_very_small)

@register("R-EXAM-13")
def _(ps: PatientState) -> bool:
    """确诊早期或局部晚期NSCLC, 准备开始治疗"""
    return (ps.cancer_type == "nsclc"
            and (ps.is_early_stage() or ps.is_locally_advanced())
            and ps.clinical_phase in ("staging", "treatment"))


# ─── R-TX: NSCLC治疗 (12条) ─────────────────────────────────

@register("R-TX-01")
def _(ps: PatientState) -> bool:
    """所有癌灶可切除, 患者可手术（仅确诊NSCLC适用）"""
    return (ps.cancer_type == "nsclc"
            and ps.clinical_phase not in ("screening", "initial_workup")
            and ps.resectable and ps.surgery_eligible)

@register("R-TX-02-A")
def _(ps: PatientState) -> bool:
    """早期NSCLC, 不能手术, 适合SABR"""
    return (ps.cancer_type == "nsclc" and ps.is_early_stage()
            and not ps.surgery_eligible and ps.sabr_eligible)

@register("R-TX-02-B")
def _(ps: PatientState) -> bool:
    """早期NSCLC, 不能手术, 不适合SABR"""
    return (ps.cancer_type == "nsclc" and ps.is_early_stage()
            and not ps.surgery_eligible and not ps.sabr_eligible)

@register("R-TX-04-A")
def _(ps: PatientState) -> bool:
    """肿瘤>=4cm或淋巴结阳性, 拟新辅助, 化免安全, 无EGFR/ALK"""
    return ((ps.diameter_mm >= 40 or ps.n_stage not in ("N0", ""))
            and ps.neoadjuvant_planned
            and ps.chemo_immunotherapy_safe
            and not ps.has_driver_mutation())

@register("R-TX-04-B")
def _(ps: PatientState) -> bool:
    """肿瘤>=4cm或淋巴结阳性, 拟新辅助, 化免不安全"""
    return ((ps.diameter_mm >= 40 or ps.n_stage not in ("N0", ""))
            and ps.neoadjuvant_planned
            and not ps.chemo_immunotherapy_safe)

@register("R-TX-04-C")
def _(ps: PatientState) -> bool:
    """肿瘤>=4cm或淋巴结阳性, 拟新辅助, 带EGFR/ALK"""
    return ((ps.diameter_mm >= 40 or ps.n_stage not in ("N0", ""))
            and ps.neoadjuvant_planned
            and ps.has_driver_mutation())

@register("R-TX-04-D")
def _(ps: PatientState) -> bool:
    """需要新辅助化免, 腺癌/大细胞/罕见"""
    return (ps.neoadjuvant_planned and ps.chemo_immunotherapy_safe
            and ps.histology in ("adenocarcinoma", "large_cell", "rare"))

@register("R-TX-04-E")
def _(ps: PatientState) -> bool:
    """需要新辅助化免, 鳞状细胞癌"""
    return (ps.neoadjuvant_planned and ps.chemo_immunotherapy_safe
            and ps.histology == "squamous")

@register("R-TX-05-A")
def _(ps: PatientState) -> bool:
    """围手术期铂类双药, 腺癌/大细胞/罕见"""
    return (ps.neoadjuvant_planned
            and ps.histology in ("adenocarcinoma", "large_cell", "rare"))

@register("R-TX-05-B")
def _(ps: PatientState) -> bool:
    """围手术期铂类双药, 鳞状细胞癌"""
    return (ps.neoadjuvant_planned
            and ps.histology == "squamous")

@register("R-TX-06-A")
def _(ps: PatientState) -> bool:
    """IIB/IIIA期, T3侵犯邻近组织, 可耐受同步"""
    return (ps.stage_in("IIB", "IIIA")
            and ps.t_stage == "T3" and ps.tumor_invades_adjacent
            and ps.concurrent_crt_tolerable)

@register("R-TX-06-B")
def _(ps: PatientState) -> bool:
    """IIB/IIIA期, T3侵犯邻近组织, 不适合同步"""
    return (ps.stage_in("IIB", "IIIA")
            and ps.t_stage == "T3" and ps.tumor_invades_adjacent
            and not ps.concurrent_crt_tolerable)

@register("R-TX-07-A")
def _(ps: PatientState) -> bool:
    """IIIA期, T4肿瘤, 可耐受同步"""
    return (ps.stage_in("IIIA")
            and ps.t_stage == "T4"
            and ps.concurrent_crt_tolerable)

@register("R-TX-07-B")
def _(ps: PatientState) -> bool:
    """IIIA期, T4肿瘤, 不适合同步"""
    return (ps.stage_in("IIIA")
            and ps.t_stage == "T4"
            and not ps.concurrent_crt_tolerable)

@register("R-TX-08")
def _(ps: PatientState) -> bool:
    """肺上沟肿瘤, 计划手术"""
    return ps.pancoast_tumor and ps.planned_treatment == "surgery"

@register("R-TX-09")
def _(ps: PatientState) -> bool:
    """N2期NSCLC, 仍有手术可能"""
    return (ps.n_stage == "N2" and ps.cancer_type == "nsclc"
            and ps.surgery_eligible)


# ─── R-POSTOP: 术后管理 (14条) ──────────────────────────────

@register("R-POSTOP-01")
def _(ps: PatientState) -> bool:
    """R0切缘, 较大IB/IIA期(>=4cm)"""
    return (ps.surgical_margin == "R0"
            and ps.stage_in("IB", "IIA")
            and ps.diameter_mm >= 40)

@register("R-POSTOP-02")
def _(ps: PatientState) -> bool:
    """R0切缘, IIB/III期, 术前未化疗"""
    return (ps.surgical_margin == "R0"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and not ps.neoadjuvant_received)

@register("R-POSTOP-03")
def _(ps: PatientState) -> bool:
    """R0切缘, EGFR阳性, 无法铂类双药"""
    return (ps.surgical_margin == "R0"
            and ps.has_egfr_sensitizing()
            and not ps.chemo_immunotherapy_safe)

@register("R-POSTOP-04")
def _(ps: PatientState) -> bool:
    """R0切缘, 化疗后, II/III期ALK阳性"""
    return (ps.surgical_margin == "R0"
            and ps.adjuvant_chemo_completed
            and ps.stage_in("IIA", "IIB", "IIIA", "IIIB", "IIIC")
            and ps.alk_rearrangement == "positive")

@register("R-POSTOP-05")
def _(ps: PatientState) -> bool:
    """R0切缘, 化疗后, IB/II/III期EGFR阳性"""
    return (ps.surgical_margin == "R0"
            and ps.adjuvant_chemo_completed
            and ps.stage_in("IB", "IIA", "IIB", "IIIA", "IIIB", "IIIC")
            and ps.has_egfr_sensitizing())

@register("R-POSTOP-06")
def _(ps: PatientState) -> bool:
    """R0切缘, 化疗后, II/III期, PD-L1>=1%, 无EGFR/ALK"""
    return (ps.surgical_margin == "R0"
            and ps.adjuvant_chemo_completed
            and ps.stage_in("IIA", "IIB", "IIIA", "IIIB", "IIIC")
            and ps.pdl1_level in (">=50%", "1-49%")
            and not ps.has_driver_mutation())

@register("R-POSTOP-07")
def _(ps: PatientState) -> bool:
    """R0切缘, 化疗后, II/III期, 无EGFR/ALK"""
    return (ps.surgical_margin == "R0"
            and ps.adjuvant_chemo_completed
            and ps.stage_in("IIA", "IIB", "IIIA", "IIIB", "IIIC")
            and not ps.has_driver_mutation())

@register("R-POSTOP-08")
def _(ps: PatientState) -> bool:
    """R0切缘, N2期, 已完成化疗"""
    return (ps.surgical_margin == "R0"
            and ps.n_stage == "N2"
            and ps.adjuvant_chemo_completed)

@register("R-POSTOP-09")
def _(ps: PatientState) -> bool:
    """R1/R2切缘, I/IIA期, 适合再手术"""
    return (ps.surgical_margin in ("R1", "R2")
            and ps.stage_in("IA", "IB", "IIA")
            and ps.re_surgery_eligible)

@register("R-POSTOP-09-B")
def _(ps: PatientState) -> bool:
    """R1/R2切缘, IB/IIA期, 已完成再手术"""
    return (ps.surgical_margin in ("R1", "R2")
            and ps.stage_in("IB", "IIA")
            and ps.re_surgery_completed)

@register("R-POSTOP-10")
def _(ps: PatientState) -> bool:
    """R1/R2切缘, I/IIA期, 再手术有并发症"""
    return (ps.surgical_margin in ("R1", "R2")
            and ps.stage_in("IA", "IB", "IIA")
            and not ps.re_surgery_eligible)

@register("R-POSTOP-11")
def _(ps: PatientState) -> bool:
    """R1/R2切缘, IIA期, 已完成放疗"""
    return (ps.surgical_margin in ("R1", "R2")
            and ps.stage_in("IIA")
            and ps.radiation_received)

@register("R-POSTOP-12")
def _(ps: PatientState) -> bool:
    """R1/R2切缘, IIB/III期, 未化疗"""
    return (ps.surgical_margin in ("R1", "R2")
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and not ps.adjuvant_chemo_completed)

@register("R-POSTOP-13")
def _(ps: PatientState) -> bool:
    """R1切缘"""
    return ps.surgical_margin == "R1"

@register("R-POSTOP-14")
def _(ps: PatientState) -> bool:
    """R2切缘"""
    return ps.surgical_margin == "R2"


# ─── R-CRT: 放化疗 (6条) ────────────────────────────────────

@register("R-CRT-00-A")
def _(ps: PatientState) -> bool:
    """某些IIB/III期NSCLC, 可耐受同步"""
    return (ps.cancer_type == "nsclc"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and ps.concurrent_crt_tolerable)

@register("R-CRT-00-B")
def _(ps: PatientState) -> bool:
    """某些IIB/III期NSCLC, 同步危害过大"""
    return (ps.cancer_type == "nsclc"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and not ps.concurrent_crt_tolerable)

@register("R-CRT-01-A")
def _(ps: PatientState) -> bool:
    """序贯放化疗, 腺癌/大细胞/罕见"""
    return (ps.crt_pathway == "sequential"
            and ps.histology in ("adenocarcinoma", "large_cell", "rare"))

@register("R-CRT-01-B")
def _(ps: PatientState) -> bool:
    """序贯放化疗, 鳞状细胞癌"""
    return (ps.crt_pathway == "sequential"
            and ps.histology == "squamous")

@register("R-CRT-02-A")
def _(ps: PatientState) -> bool:
    """同步放化疗, 腺癌/大细胞/罕见"""
    return (ps.crt_pathway == "concurrent"
            and ps.histology in ("adenocarcinoma", "large_cell", "rare"))

@register("R-CRT-02-B")
def _(ps: PatientState) -> bool:
    """同步放化疗, 鳞状细胞癌"""
    return (ps.crt_pathway == "concurrent"
            and ps.histology == "squamous")

@register("R-CRT-03")
def _(ps: PatientState) -> bool:
    """完成根治性序贯放化疗, 有EGFR ex19del/L858R"""
    return (ps.crt_completed and ps.crt_pathway == "sequential"
            and ps.has_egfr_sensitizing())

@register("R-CRT-04")
def _(ps: PatientState) -> bool:
    """完成根治性序贯放化疗, 无EGFR ex19del/L858R"""
    return (ps.crt_completed and ps.crt_pathway == "sequential"
            and not ps.has_egfr_sensitizing())


# ─── R-FU: NSCLC随访 (2条) ──────────────────────────────────

@register("R-FU-01")
def _(ps: PatientState) -> bool:
    """I/II期, 未放疗, 治疗后检查正常"""
    return (ps.cancer_type == "nsclc"
            and ps.stage_in("IA", "IB", "IIA")
            and not ps.radiation_received
            and ps.post_treatment_clear)

@register("R-FU-02")
def _(ps: PatientState) -> bool:
    """I/II期+放疗, 或III期, 治疗后检查正常"""
    return (ps.cancer_type == "nsclc"
            and ((ps.stage_in("IA", "IB", "IIA") and ps.radiation_received)
                 or ps.stage_in("IIIA", "IIIB", "IIIC"))
            and ps.post_treatment_clear)


# ═══════════════════════════════════════════════════════════════
# SCLC 规则
# ═══════════════════════════════════════════════════════════════

# ─── R-EXAM: SCLC检查 (10条) ────────────────────────────────

@register("R-EXAM-14")
def _(ps: PatientState) -> bool:
    """SCLC初始就诊, 未完成基础评估"""
    return (ps.clinical_phase == "initial_workup"
            and ps.cancer_type == "sclc"
            and not ps.basic_assessment_done)

@register("R-EXAM-15")
def _(ps: PatientState) -> bool:
    """SCLC初始就诊, 未完成基础实验室检查"""
    return (ps.clinical_phase == "initial_workup"
            and ps.cancer_type == "sclc"
            and not ps.lab_tests_done)

@register("R-EXAM-03-A")
def _(ps: PatientState) -> bool:
    """SCLC初始分期评估"""
    return (ps.cancer_type == "sclc"
            and ps.clinical_phase in ("initial_workup", "staging"))

@register("R-EXAM-16")
def _(ps: PatientState) -> bool:
    """SCLC初始分期, 头部MRI可行"""
    return (ps.cancer_type == "sclc"
            and ps.clinical_phase in ("initial_workup", "staging")
            and ps.mri_feasible)

@register("R-EXAM-03-C")
def _(ps: PatientState) -> bool:
    """SCLC初始分期, 头部MRI不可行"""
    return (ps.cancer_type == "sclc"
            and ps.clinical_phase in ("initial_workup", "staging")
            and not ps.mri_feasible)

@register("R-EXAM-04-A")
def _(ps: PatientState) -> bool:
    """SCLC局限期, 确认远处转移, PET/CT可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and not ps.pet_ct_done and ps.pet_ct_feasible)

@register("R-EXAM-04-B")
def _(ps: PatientState) -> bool:
    """SCLC局限期, 确认远处转移, PET/CT不可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and not ps.pet_ct_done and not ps.pet_ct_feasible)

@register("R-EXAM-17")
def _(ps: PatientState) -> bool:
    """存在胸腔积液, 未穿刺"""
    return ps.pleural_effusion and not ps.thoracentesis_done

@register("R-EXAM-18")
def _(ps: PatientState) -> bool:
    """存在胸腔积液, 穿刺结果不明确"""
    return (ps.pleural_effusion and ps.thoracentesis_done
            and ps.thoracentesis_result == "indeterminate")

@register("R-EXAM-19")
def _(ps: PatientState) -> bool:
    """血液检查提示骨髓扩散"""
    return ps.bone_marrow_involvement

@register("R-EXAM-20")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 计划手术或放疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and ps.planned_treatment in ("surgery", "radiation", "sabr"))

@register("R-EXAM-21")
def _(ps: PatientState) -> bool:
    """计划手术/放疗/特定系统治疗, 未完成肺功能"""
    return (ps.planned_treatment in ("surgery", "radiation", "sabr", "systemic")
            and not ps.pft_done)

@register("R-EXAM-22")
def _(ps: PatientState) -> bool:
    """已获组织标本, 未完成病理审查"""
    return ps.tissue_obtained and not ps.pathology_reviewed


# ─── R-STAGE: SCLC分期 (2条) ────────────────────────────────

@register("R-STAGE-01")
def _(ps: PatientState) -> bool:
    """TNM 1-3期, 可被根治性放疗野覆盖"""
    return (ps.cancer_type == "sclc"
            and ps.stage_in("IA", "IB", "IIA", "IIB", "IIIA", "IIIB", "IIIC")
            and ps.radiation_field_coverable)

@register("R-STAGE-02")
def _(ps: PatientState) -> bool:
    """TNM 4期, 或无法被根治性放疗野覆盖"""
    return (ps.cancer_type == "sclc"
            and (ps.stage_in("IVA", "IVB")
                 or not ps.radiation_field_coverable))


# ─── R-TX-LS: SCLC局限期治疗 (8条) ─────────────────────────

@register("R-TX-LS-01")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 不适合手术"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and not ps.surgery_eligible)

@register("R-TX-LS-01-B")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 不适合手术 (备选)"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and not ps.surgery_eligible)

@register("R-TX-LS-02")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 适合手术"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and ps.surgery_eligible)

@register("R-TX-LS-03")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 肺叶切除后, 淋巴结阴性"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and ps.lobectomy_completed
            and ps.lymph_node_status == "negative")

@register("R-TX-LS-04")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 肺叶切除后, 肺门/肺内淋巴结阳性"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and ps.lobectomy_completed
            and ps.lymph_node_status == "hilar_positive")

@register("R-TX-LS-05")
def _(ps: PatientState) -> bool:
    """SCLC局限期IA/IB/IIA, 肺叶切除后, 纵隔淋巴结阳性"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IA", "IB", "IIA")
            and ps.lobectomy_completed
            and ps.lymph_node_status == "mediastinal_positive")

@register("R-TX-LS-06")
def _(ps: PatientState) -> bool:
    """SCLC局限期IIB/IIIA/IIIB/IIIC, PS 0-2"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and ps.ecog_ps <= 2)

@register("R-TX-LS-07")
def _(ps: PatientState) -> bool:
    """SCLC局限期IIB-IIIC, PS 3-4, 体能下降由癌症导致"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and ps.ecog_ps >= 3
            and ps.ps_decline_cancer_related)

@register("R-TX-LS-08")
def _(ps: PatientState) -> bool:
    """SCLC局限期IIB-IIIC, PS 3-4, 体能下降非癌症导致"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.stage_in("IIB", "IIIA", "IIIB", "IIIC")
            and ps.ecog_ps >= 3
            and not ps.ps_decline_cancer_related)


# ─── R-TX-ES: SCLC广泛期治疗 (3条) ─────────────────────────

@register("R-TX-ES-01")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 可安全免疫治疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.immunotherapy_safe)

@register("R-TX-ES-02")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 不能安全免疫治疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and not ps.immunotherapy_safe)

@register("R-TX-ES-02-B")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 需初始全身治疗备选"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive")

@register("R-TX-ES-03")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 化疗免疫后, CR/PR/SD"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.chemo_immunotherapy_completed
            and ps.best_response in ("CR", "PR", "SD"))


# ─── R-RESP: 疗效评估 (11条) ────────────────────────────────

@register("R-RESP-00-A")
def _(ps: PatientState) -> bool:
    """SCLC局限期, 已完成同步放化疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.crt_completed and ps.crt_pathway == "concurrent")

@register("R-RESP-00-B")
def _(ps: PatientState) -> bool:
    """SCLC局限期, 正在/已完成序贯放化疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.crt_pathway == "sequential")

@register("R-RESP-00-C")
def _(ps: PatientState) -> bool:
    """SCLC局限期, 正在/已完成单纯全身治疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.systemic_only_treatment)

@register("R-RESP-00-D")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 完成2-3周期或已完成全身治疗"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and (ps.treatment_cycles_completed in (2, 3)
                 or ps.systemic_treatment_completed))

@register("R-RESP-01-A")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 每2周期评估, MRI可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_cycles_completed > 0
            and ps.treatment_cycles_completed % 2 == 0
            and ps.mri_feasible)

@register("R-RESP-01-B")
def _(ps: PatientState) -> bool:
    """SCLC广泛期, 每2周期评估, MRI不可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_cycles_completed > 0
            and ps.treatment_cycles_completed % 2 == 0
            and not ps.mri_feasible)

@register("R-RESP-02")
def _(ps: PatientState) -> bool:
    """治疗期间脑部病灶进展"""
    return ps.brain_progression_on_treatment

@register("R-RESP-03")
def _(ps: PatientState) -> bool:
    """CR/PR, 无脑转移, 无记忆障碍, 总体状况允许"""
    return (ps.best_response in ("CR", "PR")
            and not ps.brain_metastasis
            and not ps.memory_impairment
            and ps.ecog_ps <= 2)

@register("R-RESP-04-A")
def _(ps: PatientState) -> bool:
    """广泛期治疗后评估, PCI未给予, MRI可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.post_treatment_assessed
            and ps.pci_status in ("declined", "ineligible", "not_administered")
            and ps.mri_feasible)

@register("R-RESP-04-B")
def _(ps: PatientState) -> bool:
    """广泛期治疗后评估, PCI未给予, MRI不可行"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.post_treatment_assessed
            and ps.pci_status in ("declined", "ineligible", "not_administered")
            and not ps.mri_feasible)

@register("R-RESP-05")
def _(ps: PatientState) -> bool:
    """广泛期, CR/PR, 存在胸腔内残余病灶"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.best_response in ("CR", "PR")
            and ps.residual_thoracic_disease)


# ─── R-REC: 复发管理 (7条) ──────────────────────────────────

@register("R-REC-01")
def _(ps: PatientState) -> bool:
    """复发性SCLC, PS 0-2"""
    return (ps.cancer_type == "sclc" and ps.recurrent
            and ps.ecog_ps <= 2)

@register("R-REC-02")
def _(ps: PatientState) -> bool:
    """复发性SCLC, 距上次治疗<6个月"""
    return (ps.cancer_type == "sclc" and ps.recurrent
            and ps.months_since_last_treatment < 6)

@register("R-REC-02-B")
def _(ps: PatientState) -> bool:
    """复发性SCLC, 距上次治疗<6个月, PS 0-2"""
    return (ps.cancer_type == "sclc" and ps.recurrent
            and ps.months_since_last_treatment < 6
            and ps.ecog_ps <= 2)

@register("R-REC-02-C")
def _(ps: PatientState) -> bool:
    """复发性SCLC, 需二线/后线全身治疗"""
    return (ps.cancer_type == "sclc" and ps.recurrent
            and ps.treatment_line >= 2)

@register("R-REC-03")
def _(ps: PatientState) -> bool:
    """复发性SCLC, 距上次治疗>=6个月"""
    return (ps.cancer_type == "sclc" and ps.recurrent
            and ps.months_since_last_treatment >= 6)

@register("R-REC-04-A")
def _(ps: PatientState) -> bool:
    """积极治疗风险>获益, 局部症状负担不高"""
    return (ps.treatment_futile
            and not ps.high_local_symptom_burden)

@register("R-REC-04-B")
def _(ps: PatientState) -> bool:
    """积极治疗风险>获益, 局部症状负担高"""
    return (ps.treatment_futile
            and ps.high_local_symptom_burden)


# ─── R-FU: SCLC随访 (15条) ──────────────────────────────────

@register("R-FU-00")
def _(ps: PatientState) -> bool:
    """已完成治疗, 到达计划随访时间点"""
    return (ps.treatment_completed
            and ps.follow_up_due)

@register("R-FU-07")
def _(ps: PatientState) -> bool:
    """随访期间新发或加重症状"""
    return (ps.clinical_phase == "follow_up"
            and ps.new_or_worsening_symptoms)

@register("R-FU-02-A")
def _(ps: PatientState) -> bool:
    """SCLC局限期治疗后, 第1-2年"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.treatment_completed
            and ps.years_since_treatment <= 2)

@register("R-FU-02-B")
def _(ps: PatientState) -> bool:
    """SCLC局限期治疗后, 第3年"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.treatment_completed
            and ps.years_since_treatment == 3)

@register("R-FU-02-C")
def _(ps: PatientState) -> bool:
    """SCLC局限期治疗后, 第4年及以后"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "limited"
            and ps.treatment_completed
            and ps.years_since_treatment >= 4)

@register("R-FU-03-A")
def _(ps: PatientState) -> bool:
    """SCLC广泛期治疗后, 第1年"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_completed
            and ps.years_since_treatment <= 1)

@register("R-FU-03-B")
def _(ps: PatientState) -> bool:
    """SCLC广泛期治疗后, 第2-3年"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_completed
            and 2 <= ps.years_since_treatment <= 3)

@register("R-FU-03-C")
def _(ps: PatientState) -> bool:
    """SCLC广泛期治疗后, 第4-5年"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_completed
            and 4 <= ps.years_since_treatment <= 5)

@register("R-FU-03-D")
def _(ps: PatientState) -> bool:
    """SCLC广泛期治疗后, 第6年及以后"""
    return (ps.cancer_type == "sclc" and ps.sclc_stage == "extensive"
            and ps.treatment_completed
            and ps.years_since_treatment >= 6)

@register("R-FU-04-A")
def _(ps: PatientState) -> bool:
    """治疗后第1年, MRI可行"""
    return (ps.treatment_completed
            and ps.years_since_treatment <= 1
            and ps.mri_feasible)

@register("R-FU-04-B")
def _(ps: PatientState) -> bool:
    """治疗后第1年, MRI不可行"""
    return (ps.treatment_completed
            and ps.years_since_treatment <= 1
            and not ps.mri_feasible)

@register("R-FU-04-C")
def _(ps: PatientState) -> bool:
    """治疗后第2年, MRI可行"""
    return (ps.treatment_completed
            and ps.years_since_treatment == 2
            and ps.mri_feasible)

@register("R-FU-04-D")
def _(ps: PatientState) -> bool:
    """治疗后第2年, MRI不可行"""
    return (ps.treatment_completed
            and ps.years_since_treatment == 2
            and not ps.mri_feasible)

@register("R-FU-05")
def _(ps: PatientState) -> bool:
    """治疗后监测期"""
    return (ps.treatment_completed
            and ps.clinical_phase == "follow_up")

@register("R-FU-06")
def _(ps: PatientState) -> bool:
    """随访CT发现新肺结节"""
    return (ps.clinical_phase == "follow_up"
            and ps.new_nodule_on_follow_up)


# ─── R-SAE: 不良事件 (1条) ──────────────────────────────────

@register("R-SAE-01")
def _(ps: PatientState) -> bool:
    """计划或正在接受PCI"""
    return ps.pci_status in ("planned", "in_progress")


# ═══════════════════════════════════════════════════════════════
# 便捷查询函数
# ═══════════════════════════════════════════════════════════════

def evaluate_all(ps: PatientState) -> dict[str, bool]:
    """对给定 PatientState 评估所有规则, 返回 {rule_id: bool}"""
    return {rid: fn(ps) for rid, fn in CONDITION_REGISTRY.items()}


def get_triggered_rules(ps: PatientState) -> list[str]:
    """返回所有被触发(True)的规则ID列表"""
    return [rid for rid, fn in CONDITION_REGISTRY.items() if fn(ps)]


def evaluate_rule(rule_id: str, ps: PatientState) -> bool:
    """评估单条规则"""
    fn = CONDITION_REGISTRY.get(rule_id)
    if fn is None:
        raise KeyError(f"Unknown rule: {rule_id}")
    return fn(ps)
