"""
病历文本生成模块
使用LLM API生成高质量病历文本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, List, Optional
from openai_api import LLMApi
from prompts import RECORD_GENERATION_PROMPT


class RecordGenerator:
    """病历文本生成器"""
    
    def __init__(self, llm_client: LLMApi = None):
        """
        初始化生成器
        
        Args:
            llm_client: LLM API客户端
        """
        self.llm_client = llm_client or LLMApi()
    
    def _format_features(self, features: Dict) -> str:
        """格式化结节特征为文本"""
        texture_map = {1: "纯磨玻璃", 2: "部分实性", 3: "实性"}
        malignancy_map = {1: "高度良性", 2: "可能良性", 3: "不确定", 4: "可能恶性", 5: "高度恶性"}
        
        return f"""- 位置: {features.get('location', '右肺上叶')}
- 大小: {features.get('diameter_mm', 10)}mm
- 质地: {texture_map.get(features.get('texture', 3), '实性')}
- 恶性评分: {features.get('malignancy', 3)}分（{malignancy_map.get(features.get('malignancy', 3), '不确定')}）
- 毛刺征: {features.get('spiculation', 3)}分
- 分叶征: {features.get('lobulation', 3)}分
- 钙化: {features.get('calcification', 6)}分"""
    
    def generate(self, nodule_features: Dict, clinical_context: List[Dict], risk_assessment: Dict, management_plan: Dict) -> Dict:
        """
        生成单个病历
        
        Args:
            nodule_features: 结节特征
            clinical_context: 临床背景（患者列表）
            risk_assessment: 风险评估
            management_plan: 管理计划
            
        Returns:
            病历数据
        """
        # 从clinical_context中提取第一个患者信息
        if isinstance(clinical_context, list) and len(clinical_context) > 0:
            patient = clinical_context[0]
        else:
            patient = {}
        
        # 准备prompt参数
        prompt_params = {
            'patient_id': patient.get('patient_id', 'P001'),
            'age': patient.get('age', 55),
            'gender': patient.get('gender', '男'),
            'smoking_history': patient.get('smoking_history', '无'),
            'chief_complaint': patient.get('chief_complaint', '体检发现肺结节'),
            'present_illness': patient.get('present_illness', '体检发现肺结节'),
            'past_history': patient.get('past_history', '无特殊'),
            'family_history': patient.get('family_history', '无'),
            'physical_exam': patient.get('physical_exam', '一般情况良好'),
            'lab_tests': patient.get('lab_tests', '正常'),
            'location': nodule_features.get('location', '右肺上叶'),
            'diameter_mm': nodule_features.get('diameter_mm', 10),
            'size_category': nodule_features.get('size_category', '小结节'),
            'texture_desc': nodule_features.get('texture_desc', '实性'),
            'malignancy_desc': risk_assessment.get('malignancy_desc', '不确定'),
            'spiculation_desc': nodule_features.get('spiculation_desc', '无'),
            'lobulation_desc': nodule_features.get('lobulation_desc', '无'),
            'risk_assessment': risk_assessment.get('risk_level', '中危'),
            'matched_rules_text': management_plan.get('matched_rules_text', '无')
        }
        
        user_prompt = RECORD_GENERATION_PROMPT.format(**prompt_params)
        
        # 调用LLM生成病历
        record_text = self.llm_client.call(
            system_prompt="你是一位资深肺科医生，擅长撰写规范的病历文书。",
            user_prompt=user_prompt,
            temperature=0.6
        )
        
        return {
            'patient_id': patient.get('patient_id', 'P001'),
            'nodule_id': nodule_features.get('nodule_id', 'N/A'),
            'full_text': record_text,
            'patient_info': patient,
            'nodule_features': nodule_features
        }
    
    def generate_batch(self, features: Dict, patients: List[Dict], risk_assessment: Dict = None, management_plans: List[Dict] = None) -> List[Dict]:
        """
        为同一结节的多个患者生成病历
        
        Args:
            features: 结节特征
            patients: 患者列表（3个不同患者）
            risk_assessment: 风险评估
            management_plans: 管理计划列表（per-patient，含EBM规则）
            
        Returns:
            病历列表
        """
        if risk_assessment is None:
            risk_assessment = {}
        if management_plans is None:
            management_plans = [{}] * len(patients)
        
        records = []
        for patient, plan in zip(patients, management_plans):
            try:
                record = self.generate(features, [patient], risk_assessment, plan)
                records.append(record)
            except Exception as e:
                print(f"Error generating record for patient {patient.get('patient_id')}: {e}")
        
        return records