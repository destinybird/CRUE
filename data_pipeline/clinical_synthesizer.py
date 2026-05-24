"""
临床背景合成模块
根据LIDC特征生成3个不同的患者临床背景
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, List
from openai_api import LLMApi
from prompts import CLINICAL_SYNTHESIS_PROMPT


class ClinicalSynthesizer:
    """临床背景合成器 - 为每个结节生成3个不同患者"""
    
    def __init__(self, llm_client: LLMApi = None):
        """
        初始化合成器
        
        Args:
            llm_client: LLM API客户端，如果为None则创建新实例
        """
        self.llm_client = llm_client or LLMApi()
    
    def _get_texture_desc(self, texture: int) -> str:
        """质地数字转描述（LIDC 1-5分制）"""
        texture_map = {
            1: "纯磨玻璃",
            2: "磨玻璃为主",
            3: "混合密度（部分实性）",
            4: "实性为主",
            5: "完全实性"
        }
        return texture_map.get(texture, "实性")
    
    def _get_malignancy_desc(self, malignancy: int) -> str:
        """恶性程度转描述"""
        malignancy_map = {
            1: "高度良性",
            2: "可能良性",
            3: "不确定",
            4: "可能恶性",
            5: "高度恶性"
        }
        return malignancy_map.get(malignancy, "不确定")
    
    # 合法枚举值
    VALID_PHASES = {"screening", "incidental", "surveillance", "diagnostic", "treatment"}
    VALID_SURGICAL_RISK = {"low", "moderate", "high"}
    VALID_PREFERENCE = {"aggressive", "conservative", "shared_decision"}
    VALID_GROWTH = {"slow", "moderate", "rapid", None}

    def _validate_patient(self, patient: Dict, features: Dict) -> bool:
        """
        验证患者数据是否合理
        
        Args:
            patient: 患者数据
            features: 结节特征
            
        Returns:
            是否通过验证
        """
        age = patient.get('age', 0) or 0
        gender = patient.get('gender', '') or ''
        smoking = patient.get('smoking_history', '') or ''
        malignancy = features.get('malignancy', 3) or 3
        texture = features.get('texture', 3) or 3
        
        # 约束1: 年龄范围
        if not (35 <= age <= 80):
            return False
        
        # 约束2: 高恶性结节应偏向老年患者
        if malignancy >= 4 and age < 45:
            return False
        
        # 约束3: 非实性结节常见于非吸烟女性
        if texture == 1 and '重度' in smoking and '每日' in smoking:
            return False
        
        # 约束4: 低恶性结节不应有远处转移描述
        present_illness = patient.get('present_illness', '') or ''
        if malignancy <= 2 and ('转移' in present_illness or '骨痛' in present_illness):
            return False
        
        # 约束5: 枚举字段合法性
        phase = patient.get('clinical_phase')
        if phase and phase not in self.VALID_PHASES:
            return False
        
        risk = patient.get('surgical_risk')
        if risk and risk not in self.VALID_SURGICAL_RISK:
            return False
        
        pref = patient.get('patient_preference')
        if pref and pref not in self.VALID_PREFERENCE:
            return False
        
        ecog = patient.get('ecog_ps')
        if ecog is not None and not (0 <= ecog <= 4):
            return False
        
        # 约束6: 低恶性结节不应处于treatment阶段
        if malignancy <= 2 and phase == 'treatment':
            return False
        
        # 约束7: 仅treatment/diagnostic/surveillance阶段可有cancer_type/tnm_stage
        if phase not in ('treatment', 'diagnostic', 'surveillance') and patient.get('cancer_type'):
            return False
        
        # 约束8: screening/incidental阶段不应有biopsy
        if phase in ('screening', 'incidental') and patient.get('has_biopsy'):
            return False
        
        return True
    
    @staticmethod
    def build_patient_state_dict(features: Dict, patient: Dict) -> Dict:
        """
        合并影像特征 + 临床背景 → PatientState 兼容字典
        
        Args:
            features: 结节影像特征 (来自LIDC)
            patient: 临床背景 (来自LLM合成)
            
        Returns:
            可直接传入 PatientState(**d) 的字典
        """
        diameter = features.get('diameter_mm', 10)
        texture = features.get('texture', 3)
        
        # 密度分类
        density_map = {1: 'ground_glass', 2: 'ground_glass', 3: 'part_solid', 4: 'solid', 5: 'solid'}
        density = density_map.get(texture, 'solid')
        
        # 大小分类
        if diameter < 6:
            size_cat = '<6mm'
        elif diameter < 8:
            size_cat = '6-8mm'
        elif diameter < 15:
            size_cat = '8-15mm'
        elif diameter < 30:
            size_cat = '15-30mm'
        else:
            size_cat = '>30mm'
        
        return {
            # 影像特征
            'nodule_id': features.get('nodule_id', 'N/A'),
            'diameter_mm': diameter,
            'size_category': size_cat,
            'density_type': density,
            'texture_score': texture,
            'malignancy_score': features.get('malignancy', 3),
            'spiculation_score': features.get('spiculation', 3),
            'lobulation_score': features.get('lobulation', 3),
            'location': features.get('location', '右肺上叶'),
            # 人口学
            'age': patient.get('age', 60),
            'gender': 'male' if patient.get('gender', '男') == '男' else 'female',
            'smoking_pack_years': patient.get('smoking_pack_years', 0),
            # 临床阶段
            'clinical_phase': patient.get('clinical_phase', 'screening'),
            'has_symptoms': patient.get('has_symptoms', False),
            'ecog_ps': patient.get('ecog_ps', 1),
            'comorbidities': patient.get('comorbidities', []),
            'surgical_risk': patient.get('surgical_risk', 'low'),
            'prior_cancer_history': patient.get('prior_cancer_history', False),
            # 检查结果
            'has_pet_scan': patient.get('has_pet_scan', False),
            'pet_suv_max': patient.get('pet_suv_max'),
            'has_biopsy': patient.get('has_biopsy', False),
            'biopsy_result': patient.get('biopsy_result'),
            # 动态变化
            'growth_rate_category': patient.get('growth_rate_category'),
            'is_growing': patient.get('is_growing', False),
            'is_new': patient.get('is_new', True),
            'is_stable': patient.get('is_stable', False),
            'time_since_first_detection_months': patient.get('time_since_first_detection_months', 0),
            # 偏好
            'patient_preference': patient.get('patient_preference', 'shared_decision'),
            # 确诊信息 (仅treatment阶段)
            'cancer_type': patient.get('cancer_type'),
            'histology': patient.get('histology'),
            'tnm_stage': patient.get('tnm_stage'),
            'biomarkers': patient.get('biomarkers'),
            # 术后随访
            'post_treatment_clear': patient.get('post_treatment_clear', False),
            'radiation_received': patient.get('radiation_received', False),
        }

    def _diversify_phases(self, patients: List[Dict], features: Dict) -> List[Dict]:
        """
        后处理：强制为3个患者分配不同的临床阶段，
        确保EBM引擎能触发不同类别的规则（NODULE/EXAM/TREAT/FU等）。
        
        分配策略（基于恶性程度）：
          低恶性(1-2): screening, diagnostic, surveillance
          中恶性(3):    screening, diagnostic, treatment
          高恶性(4-5):  diagnostic, treatment, surveillance
        """
        malignancy = features.get('malignancy', 3)
        
        if malignancy <= 2:
            target_phases = ['screening', 'diagnostic', 'surveillance']
        elif malignancy == 3:
            target_phases = ['screening', 'diagnostic', 'treatment']
        else:
            target_phases = ['diagnostic', 'treatment', 'surveillance']
        
        for i, patient in enumerate(patients[:3]):
            phase = target_phases[i]
            patient['clinical_phase'] = phase
            
            # ── 按阶段补齐/清理关联字段，保持数据一致性 ──
            if phase == 'treatment':
                # treatment 阶段必须有确诊信息，否则 R-TREAT 规则无法触发
                if not patient.get('cancer_type'):
                    patient['cancer_type'] = 'nsclc'
                if not patient.get('histology'):
                    patient['histology'] = 'adenocarcinoma'
                if not patient.get('tnm_stage'):
                    patient['tnm_stage'] = 'IIA' if malignancy <= 3 else 'IIIA'
                patient['has_biopsy'] = True
                patient['biopsy_result'] = patient.get('biopsy_result') or 'malignant'
                patient['has_pet_scan'] = True
            elif phase == 'diagnostic':
                # diagnostic → EBM initial_workup, EXAM规则需要cancer_type='nsclc'
                patient['has_pet_scan'] = True
                patient['has_biopsy'] = True
                patient['biopsy_result'] = patient.get('biopsy_result') or 'suspicious'
                patient['cancer_type'] = 'nsclc'
                patient['histology'] = patient.get('histology') or 'adenocarcinoma'
                # diagnostic阶段不设tnm_stage（尚未完成分期）
                patient.pop('tnm_stage', None)
            elif phase == 'surveillance':
                # surveillance → EBM follow_up, FU规则需要cancer_type='nsclc' + tnm_stage
                if not patient.get('time_since_first_detection_months'):
                    patient['time_since_first_detection_months'] = 12
                patient['is_new'] = False
                patient['is_stable'] = True
                patient['cancer_type'] = 'nsclc'
                patient['histology'] = patient.get('histology') or 'adenocarcinoma'
                if not patient.get('tnm_stage'):
                    patient['tnm_stage'] = 'IA' if malignancy <= 3 else 'IIA'
                patient['has_biopsy'] = True
                patient['biopsy_result'] = patient.get('biopsy_result') or 'malignant'
                patient['post_treatment_clear'] = True
            else:
                # screening / incidental: 清理不该有的字段
                patient['has_biopsy'] = False
                patient.pop('biopsy_result', None)
                patient.pop('cancer_type', None)
                patient.pop('tnm_stage', None)
        
        return patients

    def synthesize(self, features: Dict) -> List[Dict]:
        """
        为单个结节特征生成3个不同患者
        
        Args:
            features: 结节特征字典
            
        Returns:
            3个患者数据列表
        """
        # 准备prompt参数
        prompt_params = {
            'nodule_id': features.get('nodule_id', 'N/A'),
            'location': features.get('location', '右肺上叶'),
            'diameter_mm': features.get('diameter_mm', 10),
            'malignancy_score': features.get('malignancy', 3),
            'spiculation_score': features.get('spiculation', 3),
            'texture_type': features.get('texture', 3),
            'subsolid_score': features.get('subsolid', 3),
            'lobulation_score': features.get('lobulation', 3)
        }
        
        user_prompt = CLINICAL_SYNTHESIS_PROMPT.format(**prompt_params)
        
        # 调用LLM
        patients = self.llm_client.call_with_json(
            system_prompt="你是一位资深肺科医生，擅长根据影像学特征推断合理的患者临床背景。",
            user_prompt=user_prompt,
            temperature=0.8  # 稍高温度增加多样性
        )
        
        # 验证和修正
        validated_patients = []
        for patient in patients:
            if self._validate_patient(patient, features):
                validated_patients.append(patient)
            else:
                # 如果验证失败，记录警告但仍然保留（LLM可能需要多次尝试）
                print(f"Warning: Patient {patient.get('patient_id')} failed validation")
                validated_patients.append(patient)
        
        # 确保返回3个患者
        while len(validated_patients) < 3:
            validated_patients.append(validated_patients[0].copy() if validated_patients else {})
        
        # 后处理：强制分配不同临床阶段，确保EBM规则多样性
        validated_patients = self._diversify_phases(validated_patients[:3], features)
        
        return validated_patients
    
    def synthesize_batch(self, features_list: List[Dict]) -> Dict[str, List[Dict]]:
        """
        批量生成患者背景
        
        Args:
            features_list: 结节特征列表
            
        Returns:
            {nodule_id: [患者1, 患者2, 患者3]} 字典
        """
        results = {}
        for features in features_list:
            nodule_id = features.get('nodule_id', 'unknown')
            try:
                patients = self.synthesize(features)
                results[nodule_id] = patients
            except Exception as e:
                print(f"Error synthesizing for nodule {nodule_id}: {e}")
                results[nodule_id] = []
        
        return results