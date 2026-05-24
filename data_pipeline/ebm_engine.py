"""
EBM规则引擎 - 基于condition_registry的结构化规则匹配
替代原rule_matcher的NLP文本匹配，保留logistic概率计算
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(__file__))

from patient_state import PatientState
from condition_registry import CONDITION_REGISTRY, get_triggered_rules, evaluate_all


# ── rule_id前缀 → 类别映射 ──────────────────────────────────────

_PREFIX_CATEGORY = {
    'R-NODULE':   'NODULE_MGMT',
    'R-EXAM':     'EXAM',
    'R-SCREEN':   'SCREENING',
    'R-RISK':     'RISK_ASSESS',
    'R-TREAT':    'TREATMENT',
    'R-SURG':     'SURGERY',
    'R-CHEMO':    'CHEMOTHERAPY',
    'R-RADIO':    'RADIOTHERAPY',
    'R-TARGET':   'TARGETED_THERAPY',
    'R-IMMUNO':   'IMMUNOTHERAPY',
    'R-STAGE':    'STAGING',
    'R-PATH':     'PATHOLOGY',
    'R-FOLLOW':   'FOLLOWUP',
    'R-COMOR':    'COMORBIDITY',
    'R-SMOKE':    'SMOKING',
    'R-PALLIA':   'PALLIATIVE',
    'R-MDT':      'MDT',
    'R-GENE':     'GENETIC',
    'R-PET':      'PET_CT',
    'R-BIOPSY':   'BIOPSY',
    'R-LDCT':     'LDCT_SCREENING',
}


def _get_category(rule_id: str) -> str:
    for prefix, cat in _PREFIX_CATEGORY.items():
        if rule_id.startswith(prefix):
            return cat
    return 'OTHER'


def _get_rule_doc(rule_id: str) -> str:
    func = CONDITION_REGISTRY.get(rule_id)
    if func and func.__doc__:
        return func.__doc__.strip()
    return rule_id


# ── logistic概率计算（保留自原rule_matcher） ──────────────────────

def _compute_malignancy_probability(features: dict) -> dict:
    diameter = features.get('diameter_mm', 10.0) or 10.0
    malignancy = features.get('malignancy', 3) or 3
    spiculation = features.get('spiculation', 3) or 3
    lobulation = features.get('lobulation', 3) or 3
    texture = features.get('texture', 3) or 3

    intercept = -6.7668
    coefs = {
        'diameter': 0.0391, 'malignancy': 0.9067,
        'spiculation': 0.2953, 'lobulation': 0.1654, 'texture': 0.3104,
    }

    logit = (intercept
             + coefs['diameter'] * diameter
             + coefs['malignancy'] * malignancy
             + coefs['spiculation'] * spiculation
             + coefs['lobulation'] * lobulation
             + coefs['texture'] * texture)

    probability = 1.0 / (1.0 + math.exp(-logit))

    if probability >= 0.65:
        risk_level = '高风险'
    elif probability >= 0.30:
        risk_level = '中风险'
    else:
        risk_level = '低风险'

    factors = []
    if diameter > 15:
        factors.append(f'结节较大({diameter:.1f}mm)')
    if malignancy >= 4:
        factors.append(f'恶性评分高({malignancy}/5)')
    if spiculation >= 4:
        factors.append(f'毛刺征明显({spiculation}/5)')
    if lobulation >= 4:
        factors.append(f'分叶征明显({lobulation}/5)')
    if texture >= 4:
        factors.append(f'实性成分多(texture={texture}/5)')

    return {
        'risk_level': risk_level,
        'probability': round(probability, 4),
        'factors': factors,
    }


# ── LIDC特征 + 患者数据 → PatientState ─────────────────────────

_TEXTURE_TO_TYPE = {
    1: 'ground_glass', 2: 'ground_glass',
    3: 'part_solid',
    4: 'solid', 5: 'solid',
}

_MAL_TO_RISK = {
    1: 'low', 2: 'low', 3: 'low',
    4: 'high', 5: 'high',
}

# ── Synthesizer phase → EBM condition_registry phase 映射 ──
_SYNTH_TO_EBM_PHASE = {
    'screening': 'screening',
    'incidental': 'screening',
    'diagnostic': 'initial_workup',
    'treatment': 'treatment',
    'staging': 'staging',
    'surveillance': 'follow_up',
    'follow_up': 'follow_up',
    'initial_workup': 'initial_workup',
}


def build_patient_state(features: dict, patient_data: dict = None) -> PatientState:
    patient_data = patient_data or {}
    ps = PatientState()

    diameter = features.get('diameter_mm', 10.0) or 10.0
    texture = features.get('texture', 3) or 3
    malignancy = features.get('malignancy', 3) or 3

    ps.diameter_mm = diameter
    ps.density = _TEXTURE_TO_TYPE.get(texture, 'solid')
    ps.risk_level = _MAL_TO_RISK.get(malignancy, 'low')
    ps.tumor_location = features.get('location', '右肺上叶')
    ps.texture = texture
    ps.malignancy = malignancy

    if diameter < 6:
        ps.nodule_size_category = '<6mm'
    elif diameter < 8:
        ps.nodule_size_category = '6-8mm'
    elif diameter < 15:
        ps.nodule_size_category = '8-15mm'
    elif diameter < 30:
        ps.nodule_size_category = '15-30mm'
    else:
        ps.nodule_size_category = '>=30mm'

    ps.spiculation = features.get('spiculation', 3) or 3
    ps.lobulation = features.get('lobulation', 3) or 3
    ps.calcification = features.get('calcification', 6) or 6
    ps.nodule_count = 1
    ps.multiple_nodules = False

    # 筛查阶段尚未确诊，不应默认为nsclc
    ps.cancer_type = 'undetermined'
    ps.histology = 'none'

    if patient_data:
        ps.age = patient_data.get('age', 55) or 55
        ps.gender = patient_data.get('gender', '男')

        smoking = patient_data.get('smoking_history', '') or ''
        if '从不' in smoking or '无' in smoking or '不吸' in smoking:
            ps.smoking_status = 'never'
            ps.pack_years = 0
        elif '戒' in smoking:
            ps.smoking_status = 'former'
            ps.pack_years = patient_data.get('pack_years', 20) or 20
        else:
            ps.smoking_status = 'current'
            ps.pack_years = patient_data.get('pack_years', 30) or 30

        history = patient_data.get('past_history', '') or ''
        family = patient_data.get('family_history', '') or ''
        present = patient_data.get('present_illness', '') or ''
        all_text = f"{history} {family} {present}"

        ps.cancer_history = '肿瘤' in all_text or '癌' in all_text or '恶性' in all_text
        ps.family_cancer_history = '癌' in family or '肿瘤' in family
        ps.copd = 'COPD' in all_text or '慢阻肺' in all_text
        ps.pulmonary_fibrosis = '纤维化' in all_text or '间质' in all_text
        ps.emphysema = '肺气肿' in all_text
        ps.asbestos_exposure = '石棉' in all_text

        symptoms = patient_data.get('symptoms', '') or ''
        ps.hemoptysis = '咯血' in symptoms or '咯血' in present
        ps.weight_loss = '体重' in symptoms or '消瘦' in symptoms
        ps.cough_persistent = '咳嗽' in symptoms

        ps.ecog_ps = patient_data.get('ecog_ps', 0) or 0

        # ── 临床阶段字段：覆盖默认值 (来自ClinicalSynthesizer透传) ──
        if patient_data.get('clinical_phase'):
            raw_phase = patient_data['clinical_phase']
            ps.clinical_phase = _SYNTH_TO_EBM_PHASE.get(raw_phase, raw_phase)
        if patient_data.get('cancer_type'):
            ps.cancer_type = patient_data['cancer_type'].lower()
        if patient_data.get('histology'):
            ps.histology = patient_data['histology']
        if patient_data.get('tnm_stage'):
            ps.tnm_stage = patient_data['tnm_stage']
        if patient_data.get('post_treatment_clear'):
            ps.post_treatment_clear = True
        # ── 映射 ClinicalSynthesizer 字段 → PatientState 字段 ──
        if patient_data.get('has_biopsy'):
            ps.tissue_obtained = True
            ps.pathology_reviewed = True
        if patient_data.get('has_pet_scan'):
            ps.pet_ct_done = True
        surgical_risk = patient_data.get('surgical_risk', 'low')
        if surgical_risk == 'high':
            ps.surgery_eligible = False
        if patient_data.get('has_symptoms'):
            ps.new_or_worsening_symptoms = True

    return ps


# ── 主入口：生成管理方案 ──────────────────────────────────────

def generate_ebm_plan(features: dict, patient_data: dict = None) -> dict:
    risk_info = _compute_malignancy_probability(features)

    ps = build_patient_state(features, patient_data)

    # 将logistic风险回写到ps，供condition_registry规则使用
    _risk_cn_to_en = {'高风险': 'high', '中风险': 'intermediate', '低风险': 'low'}
    ps.risk_level = _risk_cn_to_en.get(risk_info['risk_level'], ps.risk_level)

    triggered_ids = get_triggered_rules(ps)

    matched_rules = []
    for rule_id in triggered_ids:
        matched_rules.append({
            'rule_id': rule_id,
            'category': _get_category(rule_id),
            'description': _get_rule_doc(rule_id),
        })

    recommendation = _extract_recommendation(matched_rules, risk_info)

    # 构建matched_rules_text供下游record_generator/dialog_generator使用
    if matched_rules:
        rules_text_lines = [f"[{r['rule_id']}] {r['description']}" for r in matched_rules]
        matched_rules_text = '\n'.join(rules_text_lines)
    else:
        matched_rules_text = '无匹配规则'

    return {
        'malignancy_risk': risk_info,
        'fleischner_rule': {
            'recommendation': recommendation,
            'matched_count': len(matched_rules),
        },
        'matched_rules': matched_rules,
        'patient_state_summary': {
            'diameter_mm': ps.diameter_mm,
            'density': ps.density,
            'risk_level': ps.risk_level,
            'age': ps.age,
            'smoking_status': ps.smoking_status,
        },
        # ── 顶层便捷key，供record_generator/dialog_generator直接.get() ──
        'risk_level': risk_info['risk_level'],
        'management_summary': recommendation,
        'matched_rules_text': matched_rules_text,
    }


def _extract_recommendation(matched_rules: list, risk_info: dict) -> str:
    if not matched_rules:
        risk = risk_info['risk_level']
        if risk == '高风险':
            return '建议进一步检查（PET-CT或活检），未匹配到具体EBM规则'
        elif risk == '中风险':
            return '建议3-6个月随访CT，未匹配到具体EBM规则'
        else:
            return '建议12个月随访CT或年度筛查，未匹配到具体EBM规则'

    priority_cats = ('SCREENING', 'EXAM', 'NODULE_MGMT', 'LDCT_SCREENING')
    for rule in matched_rules:
        if rule['category'] in priority_cats:
            return rule['description']

    return matched_rules[0]['description']


# ── 包装类：供 main_pipeline 以 OOP 方式调用 ─────────────────────

class EBMEngine:
    """EBM规则引擎包装类，将 build_patient_state_dict 输出的合并字典
    拆分为 features / patient_data 后调用 generate_ebm_plan。"""

    def evaluate(self, patient_state: dict) -> dict:
        # 从合并字典中提取影像特征（key名映射）
        features = {
            'diameter_mm': patient_state.get('diameter_mm', 10.0),
            'malignancy':  patient_state.get('malignancy_score', 3),
            'spiculation': patient_state.get('spiculation_score', 3),
            'lobulation':  patient_state.get('lobulation_score', 3),
            'texture':     patient_state.get('texture_score', 3),
            'location':    patient_state.get('location', '右肺上叶'),
        }

        # 提取临床背景
        gender_raw = patient_state.get('gender', 'male')
        gender_cn = '男' if gender_raw in ('male', '男') else '女'

        pack_years = patient_state.get('smoking_pack_years', 0) or 0
        if pack_years == 0:
            smoking_history = '从不吸烟'
        elif pack_years > 0:
            smoking_history = f'吸烟{pack_years}包年'
        else:
            smoking_history = ''

        comorbidities = patient_state.get('comorbidities', []) or []
        past_history = ' '.join(comorbidities) if comorbidities else ''

        patient_data = {
            'age':             patient_state.get('age', 55),
            'gender':          gender_cn,
            'smoking_history':  smoking_history,
            'pack_years':      pack_years,
            'past_history':    past_history,
            'family_history':  '',
            'present_illness': '',
            'symptoms':        '',
            'ecog_ps':         patient_state.get('ecog_ps', 0),
            # ── 临床阶段字段透传 (来自ClinicalSynthesizer) ──
            'clinical_phase':       patient_state.get('clinical_phase'),
            'cancer_type':          patient_state.get('cancer_type'),
            'histology':            patient_state.get('histology'),
            'tnm_stage':            patient_state.get('tnm_stage'),
            'has_biopsy':           patient_state.get('has_biopsy', False),
            'biopsy_result':        patient_state.get('biopsy_result'),
            'has_pet_scan':         patient_state.get('has_pet_scan', False),
            'pet_suv_max':          patient_state.get('pet_suv_max'),
            'surgical_risk':        patient_state.get('surgical_risk', 'low'),
            'patient_preference':   patient_state.get('patient_preference'),
            'is_growing':           patient_state.get('is_growing', False),
            'growth_rate_category': patient_state.get('growth_rate_category'),
            'has_symptoms':         patient_state.get('has_symptoms', False),
            'post_treatment_clear':  patient_state.get('post_treatment_clear', False),
        }

        return generate_ebm_plan(features, patient_data)
