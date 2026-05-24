
"""
Record Generator Module
病历生成模块：基于翻译结果和匹配规则生成临床病历
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class RecordGenerator:
    """病历生成器"""
    
    # 性别映射
    GENDER_MAP = {0: '女', 1: '男'}
    
    # 吸烟状态
    SMOKING_STATUS = ['从不吸烟', '已戒烟', '偶尔吸烟', '经常吸烟']
    
    def __init__(self):
        """初始化病历生成器"""
        self.record_templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """加载病历模板"""
        return {
            'chief_complaint': '体检发现肺部结节{duration}。',
            'present_illness': (
                '患者{gender}性，{age}岁，{smoking_status}。'
                '{duration}前体检行胸部CT检查发现肺部结节。'
                '无咳嗽、咳痰、咯血、胸痛、呼吸困难等症状。'
                '无发热、盗汗、体重下降等全身症状。'
            ),
            'imaging_findings': (
                '胸部CT示：{location}可见一{size_category}，'
                '大小约{diameter_mm}mm，{texture_desc}，'
                '边缘{margin_desc}{spiculation_desc}{lobulation_desc}，'
                '形态{sphericity_desc}。'
                '{calcification_desc}。'
                '纵隔未见明显肿大淋巴结。'
            ),
            'assessment': (
                '根据影像学特征分析：\n'
                '1. 结节大小：{diameter_mm}mm，属于{size_category}\n'
                '2. 密度特征：{texture_desc}\n'
                '3. 边缘特征：{margin_desc}\n'
                '4. 恶性风险评估：{malignancy_desc}\n'
                '综合评估：{risk_assessment}'
            ),
            'plan': '{recommendations}'
        }
    
    def _generate_patient_info(self, translated: Dict) -> Dict:
        """生成患者基本信息"""
        import random
        random.seed(hash(str(translated.get('patient_id', ''))))
        
        patient_info = {
            'patient_id': translated.get('patient_id', 'UNKNOWN'),
            'gender': self.GENDER_MAP[random.randint(0, 1)],
            'age': random.randint(45, 75),
            'smoking_status': random.choice(self.SMOKING_STATUS),
            'visit_date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            'duration': f'{random.randint(1, 12)}个月'
        }
        return patient_info
    
    def _determine_location(self, nodule_id: int) -> str:
        """确定结节位置"""
        locations = [
            '右肺上叶', '右肺中叶', '右肺下叶',
            '左肺上叶', '左肺下叶'
        ]
        return locations[int(nodule_id) % len(locations)]
    
    def _assess_risk(self, translated: Dict) -> str:
        """评估恶性风险"""
        malignancy = translated.get('malignancy_score', 3)
        spiculation = translated.get('spiculation_score', 1)
        texture = translated.get('texture_score', 4)
        
        risk_score = malignancy * 0.4 + spiculation * 0.3 + (texture / 5) * 0.3
        
        if risk_score >= 3.5:
            return '高度怀疑恶性，建议进一步检查或手术切除'
        elif risk_score >= 2.5:
            return '中度可疑，建议短期随访或PET-CT检查'
        else:
            return '低度可疑，建议定期随访观察'
    
    def generate_record(self, translated: Dict, matched_rules: List[Dict] = None) -> Dict:
        """生成完整病历"""
        # 患者信息
        patient_info = self._generate_patient_info(translated)
        
        # 结节位置
        location = self._determine_location(translated.get('nodule_id', 1))
        
        # 风险评估
        risk_assessment = self._assess_risk(translated)
        
        # 处理边缘描述
        spiculation_desc = ''
        if translated.get('spiculation_desc', '无毛刺') != '无毛刺':
            spiculation_desc = f'，{translated["spiculation_desc"]}'
        
        lobulation_desc = ''
        if translated.get('lobulation_desc', '无分叶') != '无分叶':
            lobulation_desc = f'，{translated["lobulation_desc"]}'
        
        calcification_desc = translated.get('calcification_desc', '无钙化')
        if calcification_desc != '无钙化':
            calcification_desc = f'可见{calcification_desc}'
        else:
            calcification_desc = '未见明显钙化'
        
        # 模板变量
        template_vars = {
            **patient_info,
            'location': location,
            'diameter_mm': translated.get('diameter_mm', 20),
            'size_category': translated.get('size_category', '结节'),
            'texture_desc': translated.get('texture_desc', '实性'),
            'margin_desc': translated.get('margin_desc', '边缘清晰'),
            'spiculation_desc': spiculation_desc,
            'lobulation_desc': lobulation_desc,
            'sphericity_desc': translated.get('sphericity_desc', '类圆形'),
            'calcification_desc': calcification_desc,
            'malignancy_desc': translated.get('malignancy_desc', '不确定'),
            'risk_assessment': risk_assessment
        }
        
        # 生成各部分
        chief_complaint = self.record_templates['chief_complaint'].format(**template_vars)
        present_illness = self.record_templates['present_illness'].format(**template_vars)
        imaging_findings = self.record_templates['imaging_findings'].format(**template_vars)
        assessment = self.record_templates['assessment'].format(**template_vars)
        
        # 处理建议
        if matched_rules and len(matched_rules) > 0:
            recommendations = []
            for item in matched_rules[:3]:  # 取前3条
                rule = item['rule']
                recommendations.append(f"- {rule['then_action']}")
            plan = '基于EBM规则的诊疗建议：\n' + '\n'.join(recommendations)
        else:
            plan = f'建议：{risk_assessment}'
        
        # 组装病历
        record = {
            'patient_info': patient_info,
            'nodule_info': {
                'location': location,
                'diameter_mm': template_vars['diameter_mm'],
                'size_category': template_vars['size_category'],
                'texture': template_vars['texture_desc']
            },
            'medical_record': {
                'chief_complaint': chief_complaint,
                'present_illness': present_illness,
                'imaging_findings': imaging_findings,
                'assessment': assessment,
                'plan': plan
            },
            'full_text': f"""【病历记录】

患者ID：{patient_info['patient_id']}
就诊日期：{patient_info['visit_date']}

【主诉】
{chief_complaint}

【现病史】
{present_illness}

【影像学检查】
{imaging_findings}

【诊断评估】
{assessment}

【诊疗计划】
{plan}"""
        }
        
        return record
    
    def generate_conversation(self, record: Dict) -> List[Dict]:
        """生成医患对话"""
        patient_info = record['patient_info']
        nodule_info = record['nodule_info']
        
        conversations = [
            {
                'role': 'user',
                'content': f'医生您好，我{patient_info["age"]}岁，最近体检发现肺部有个结节，很担心，想咨询一下。'
            },
            {
                'role': 'assistant',
                'content': f'您好，我理解您的担心。请把您的CT报告给我看一下，我帮您分析一下结节的情况。'
            },
            {
                'role': 'user',
                'content': f'报告上写的是{nodule_info["location"]}有个{nodule_info["diameter_mm"]}mm的结节，密度是{nodule_info["texture"]}。'
            },
            {
                'role': 'assistant',
                'content': record['medical_record']['assessment'].replace('\n', ' ')
            },
            {
                'role': 'user',
                'content': '那我应该怎么办？需要手术吗？'
            },
            {
                'role': 'assistant',
                'content': record['medical_record']['plan'].replace('\n', ' ')
            }
        ]
        
        return conversations


if __name__ == '__main__':
    # 测试
    test_translated = {
        'patient_id': 'LIDC-0157',
        'nodule_id': 3,
        'diameter_mm': 18.5,
        'size_category': '结节(8-30mm)',
        'malignancy_desc': '可能恶性',
        'spiculation_desc': '明显毛刺',
        'lobulation_desc': '中等分叶',
        'margin_desc': '边缘模糊',
        'texture_desc': '实性',
        'calcification_desc': '无钙化',
        'sphericity_desc': '类圆形',
        'malignancy_score': 4,
        'spiculation_score': 4,
        'texture_score': 4
    }
    
    generator = RecordGenerator()
    record = generator.generate_record(test_translated)
    
    print(record['full_text'])
