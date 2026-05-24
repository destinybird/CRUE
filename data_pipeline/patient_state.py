"""
PatientState — 统一患者状态数据模型
覆盖全部131条EBM规则所需的临床维度（77个字段）
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class PatientState:
    """
    患者完整临床状态，供 condition_registry 中的条件函数读取。
    所有字段均有默认值，可按需填充。
    字段名与 condition_registry.py 中 ps.xxx 完全一致。
    """

    # ── 结节特征 (来自LIDC / 影像) ──────────────────────────
    nodule_count: int = 1
    density: str = "solid"                       # solid / ground_glass / part_solid
    diameter_mm: float = 0.0
    solid_component_mm: float = 0.0              # 部分实性结节的实性成分大小(mm)
    risk_level: str = "low"                      # low / high

    # ── LIDC原始评分 (保留用于logistic概率计算) ────────────
    spiculation: int = 3
    lobulation: int = 3
    calcification: int = 3
    sphericity: int = 3
    texture: int = 3                             # 1-5, 映射→density
    malignancy: int = 3                          # 1-5, 映射→risk score

    # ── 癌症分类 ────────────────────────────────────────────
    cancer_type: str = "nsclc"                   # nsclc / sclc / undetermined
    histology: str = "adenocarcinoma"            # adenocarcinoma / squamous / large_cell / rare / none

    # ── TNM分期 ─────────────────────────────────────────────
    tnm_stage: str = ""                          # IA/IB/IIA/IIB/IIIA/IIIB/IIIC/IV
    t_stage: str = ""                            # T1/T2/T3/T4
    n_stage: str = ""                            # N0/N1/N2/N3
    sclc_stage: str = ""                         # limited / extensive / ""

    # ── 生物标志物 ──────────────────────────────────────────
    egfr_mutation: str = "negative"              # exon19del / L858R / other / negative / unknown
    alk_rearrangement: str = "negative"          # positive / negative / unknown
    pdl1_level: str = "unknown"                  # >=50% / 1-49% / <1% / unknown

    # ── 体能与耐受性 ────────────────────────────────────────
    ecog_ps: int = 0                             # ECOG 0-4
    surgery_eligible: bool = True
    sabr_eligible: bool = True
    concurrent_crt_tolerable: bool = True
    immunotherapy_safe: bool = True
    chemo_immunotherapy_safe: bool = True
    mri_feasible: bool = True
    pet_ct_feasible: bool = True

    # ── 临床阶段 / 路径 ─────────────────────────────────────
    clinical_phase: str = "screening"            # screening / initial_workup / staging /
                                                 # treatment / post_surgery / post_crt /
                                                 # follow_up / recurrence / palliative

    # ── 检查完成状态 ────────────────────────────────────────
    basic_assessment_done: bool = False
    lab_tests_done: bool = False
    chest_ct_done: bool = False
    chest_ct_days_ago: int = 0
    pet_ct_done: bool = False
    brain_mri_done: bool = False
    bronchoscopy_done: bool = False
    pft_done: bool = False                       # 肺功能检查
    pathology_reviewed: bool = False
    thoracentesis_done: bool = False
    thoracentesis_result: str = ""               # positive / negative / indeterminate / ""
    tissue_obtained: bool = False                # 组织取样完成

    # ── 肿瘤局部特征 ────────────────────────────────────────
    tumor_location: str = ""
    pancoast_tumor: bool = False
    tumor_invades_adjacent: bool = False         # T3侵犯邻近组织
    tumor_near_mediastinum: bool = False
    tumor_very_small: bool = False
    tumor_opposite_mediastinum: bool = False
    pleural_effusion: bool = False
    bone_marrow_involvement: bool = False
    residual_thoracic_disease: bool = False
    brain_metastasis: bool = False
    radiation_field_coverable: bool = True       # 放射野可覆盖

    # ── 可切除性 ────────────────────────────────────────────
    resectable: bool = True
    mediastinal_staging_needed: bool = False

    # ── 治疗状态 ────────────────────────────────────────────
    planned_treatment: str = ""                  # surgery / sabr / neoadjuvant / crt_concurrent /
                                                 # crt_sequential / systemic / palliative / ""
    neoadjuvant_planned: bool = False
    neoadjuvant_received: bool = False
    adjuvant_chemo_completed: bool = False
    radiation_received: bool = False
    surgery_completed: bool = False
    lobectomy_completed: bool = False             # 肺叶切除完成
    surgical_margin: str = ""                    # R0 / R1 / R2 / ""
    lymph_node_status: str = ""                  # negative / hilar_positive / mediastinal_positive / ""
    re_surgery_eligible: bool = False
    re_surgery_completed: bool = False
    crt_pathway: str = ""                        # concurrent / sequential / ""
    crt_completed: bool = False                  # CRT完成
    treatment_completed: bool = False
    systemic_treatment_completed: bool = False   # 全身治疗完成
    systemic_only_treatment: bool = False        # 仅全身治疗(无手术/放疗)
    chemo_immunotherapy_completed: bool = False   # 化疗+免疫完成
    treatment_futile: bool = False               # 治疗无效/不可行

    # ── 化疗周期 ────────────────────────────────────────────
    treatment_cycles_completed: int = 0          # 已完成治疗周期数
    treatment_line: int = 1                      # 治疗线数

    # ── 疗效评估 ────────────────────────────────────────────
    best_response: str = ""                      # CR / PR / SD / PD / ""
    brain_progression_on_treatment: bool = False
    post_treatment_assessed: bool = False         # 治疗后评估完成
    post_treatment_clear: bool = False            # 治疗后无残留

    # ── PCI (预防性颅脑照射) ────────────────────────────────
    pci_status: str = ""                         # administered / declined / ineligible /
                                                 # not_administered / ""
    memory_impairment: bool = False

    # ── 随访 ────────────────────────────────────────────────
    years_since_treatment: float = 0.0           # 治疗后年数
    follow_up_due: bool = False                  # 是否到随访时间
    new_or_worsening_symptoms: bool = False      # 新发/加重症状
    new_nodule_on_follow_up: bool = False        # 随访发现新结节

    # ── 复发 ────────────────────────────────────────────────
    recurrent: bool = False                      # 复发
    months_since_last_treatment: int = 0         # 距上次全身治疗月数
    ps_decline_cancer_related: bool = False      # PS下降由癌症导致
    treatment_risk_exceeds_benefit: bool = False
    high_local_symptom_burden: bool = False       # 高局部症状负担

    # ── 人口学 (来自clinical_synthesizer) ───────────────────
    age: int = 60
    gender: str = "male"
    smoking_history: str = ""
    present_illness: str = ""

    # ── 辅助字段 ────────────────────────────────────────────
    matched_rule_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转为字典，兼容现有pipeline"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PatientState":
        """从字典构建，忽略未知字段"""
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})

    # ── 便捷查询方法 ────────────────────────────────────────

    def stage_in(self, *stages: str) -> bool:
        """检查tnm_stage是否在给定列表中 (大小写不敏感)"""
        s = self.tnm_stage.upper().replace(" ", "")
        return any(s == st.upper().replace(" ", "") for st in stages)

    def stage_numeric(self) -> int:
        """将tnm_stage转为数字用于比较: IA=10,IB=11,IIA=20,...,IV=40"""
        mapping = {
            "IA": 10, "IB": 11,
            "IIA": 20, "IIB": 21,
            "IIIA": 30, "IIIB": 31, "IIIC": 32,
            "IV": 40,
        }
        return mapping.get(self.tnm_stage.upper().replace(" ", ""), 0)

    def has_egfr_sensitizing(self) -> bool:
        return self.egfr_mutation in ("exon19del", "L858R")

    def has_driver_mutation(self) -> bool:
        return self.egfr_mutation not in ("negative", "unknown") or \
               self.alk_rearrangement == "positive"

    def is_early_stage(self) -> bool:
        return self.stage_numeric() < 30

    def is_locally_advanced(self) -> bool:
        return 30 <= self.stage_numeric() < 40

    def is_advanced(self) -> bool:
        return self.stage_numeric() >= 40
