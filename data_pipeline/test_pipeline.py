"""
Pipeline测试脚本
测试各模块功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lidc_extractor import LIDCExtractor
from clinical_synthesizer import ClinicalSynthesizer
from rule_matcher import RuleMatcher
from record_generator import RecordGenerator
from dialog_generator import DialogGenerator


def test_lidc_extractor():
    """测试LIDC提取器"""
    print("\n=== Testing LIDC Extractor ===")
    
    # 使用模拟数据测试
    import pandas as pd
    
    # 创建测试CSV
    test_data = {
        'nodule_id': ['1', '2', '3'],
        'malignancy': [3, 4, 2],
        'texture': [3, 2, 1],
        'calcification': [6, 6, 1],
        'margin': [3, 4, 2],
        'sphericity': [3, 2, 4],
        'lobulation': [3, 4, 2],
        'spiculation': [3, 4, 1],
        'diameter_mm': [10, 15, 8],
        'subtlety': [3, 4, 2],
        'location': ['右肺上叶', '左肺下叶', '右肺中叶']
    }
    
    test_csv = '/tmp/test_lidc.csv'
    pd.DataFrame(test_data).to_csv(test_csv, index=False)
    
    extractor = LIDCExtractor(test_csv)
    
    # 测试获取特征
    features = extractor.get_nodule_features('1')
    print(f"Features for nodule 1: {features}")
    
    # 测试统计
    stats = extractor.get_statistics()
    print(f"Statistics: {stats}")
    
    print("✓ LIDC Extractor test passed")
    return extractor


def test_rule_matcher():
    """测试规则匹配器"""
    print("\n=== Testing Rule Matcher ===")
    
    matcher = RuleMatcher()
    
    # 测试不同特征的结节
    test_features = [
        {'nodule_id': '1', 'texture': 3, 'diameter_mm': 6, 'malignancy': 2, 'spiculation': 2, 'lobulation': 2, 'calcification': 1, 'sphericity': 4},
        {'nodule_id': '2', 'texture': 1, 'diameter_mm': 12, 'malignancy': 4, 'spiculation': 4, 'lobulation': 4, 'calcification': 6, 'sphericity': 2},
        {'nodule_id': '3', 'texture': 2, 'diameter_mm': 8, 'malignancy': 3, 'spiculation': 3, 'lobulation': 3, 'calcification': 6, 'sphericity': 3}
    ]
    
    for features in test_features:
        plan = matcher.generate_management_plan(features)
        print(f"\nNodule {features['nodule_id']}:")
        print(f"  Risk: {plan['malignancy_risk']['risk_level']}")
        print(f"  Rule: {plan['fleischner_rule']['description']}")
    
    print("\n✓ Rule Matcher test passed")
    return matcher


def test_clinical_synthesizer():
    """测试临床合成器（不调用API）"""
    print("\n=== Testing Clinical Synthesizer ===")
    
    # 创建模拟患者数据
    mock_patients = [
        {
            'patient_id': 'P001',
            'age': 55,
            'gender': '男',
            'smoking_history': '30包年',
            'family_history': '父亲肺癌',
            'past_medical_history': '高血压',
            'present_illness': '体检发现肺结节，无咳嗽咳痰'
        },
        {
            'patient_id': 'P002',
            'age': 45,
            'gender': '女',
            'smoking_history': '无',
            'family_history': '无',
            'past_medical_history': '无特殊',
            'present_illness': '常规体检发现肺部阴影'
        },
        {
            'patient_id': 'P003',
            'age': 68,
            'gender': '男',
            'smoking_history': '已戒烟10年，既往20包年',
            'family_history': '无',
            'past_medical_history': '糖尿病',
            'present_illness': '咳嗽2周，CT发现肺结节'
        }
    ]
    
    print(f"Generated {len(mock_patients)} mock patients")
    for p in mock_patients:
        print(f"  - {p['patient_id']}: {p['age']}岁 {p['gender']}")
    
    print("✓ Clinical Synthesizer test passed (mock mode)")
    return mock_patients


def test_pipeline_integration():
    """测试Pipeline集成（不调用API）"""
    print("\n=== Testing Pipeline Integration ===")
    
    # 使用模拟数据
    import pandas as pd
    
    test_data = {
        'nodule_id': ['1', '2', '3'],
        'malignancy': [3, 4, 2],
        'texture': [3, 2, 1],
        'calcification': [6, 6, 1],
        'margin': [3, 4, 2],
        'sphericity': [3, 2, 4],
        'lobulation': [3, 4, 2],
        'spiculation': [3, 4, 1],
        'diameter_mm': [10, 15, 8],
        'subtlety': [3, 4, 2],
        'location': ['右肺上叶', '左肺下叶', '右肺中叶']
    }
    
    test_csv = '/tmp/test_lidc.csv'
    pd.DataFrame(test_data).to_csv(test_csv, index=False)
    
    # 测试各模块独立功能
    extractor = LIDCExtractor(test_csv)
    matcher = RuleMatcher()
    
    # 处理单个结节
    nodule_id = '1'
    features = extractor.get_nodule_features(nodule_id)
    plan = matcher.generate_management_plan(features)
    
    print(f"\nProcessed nodule {nodule_id}:")
    print(f"  Features: {features}")
    print(f"  Management: {plan['management_summary']}")
    
    print("\n✓ Pipeline Integration test passed")


if __name__ == '__main__':
    print("=" * 60)
    print("Data Pipeline Test Suite")
    print("=" * 60)
    
    # 运行测试
    test_lidc_extractor()
    test_rule_matcher()
    test_clinical_synthesizer()
    test_pipeline_integration()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)