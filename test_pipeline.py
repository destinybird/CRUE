"""
Pipeline测试脚本
测试data_pipeline各模块功能（不依赖LLM API）
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from data_pipeline import (
    LIDCExtractor,
    RuleMatcher
)


def test_lidc_extractor(csv_path: str):
    """测试LIDCExtractor模块"""
    print("\n" + "="*60)
    print("测试 LIDCExtractor 模块")
    print("="*60)
    
    try:
        # 初始化
        extractor = LIDCExtractor(csv_path)
        print("✓ 初始化成功")
        
        # 获取统计信息
        stats = extractor.get_statistics()
        print(f"\n统计信息:")
        print(f"  - 总结节数: {stats['total_nodules']}")
        print(f"  - 恶性分布: {stats.get('malignancy_dist', 'N/A')}")
        
        # 获取所有结节ID
        all_ids = extractor.get_all_nodule_ids()
        print(f"\n✓ 获取到 {len(all_ids)} 个结节ID")
        print(f"  示例ID: {all_ids[:5]}")
        
        # 获取随机结节
        random_ids = extractor.get_random_nodules(3)
        print(f"\n✓ 随机获取 {len(random_ids)} 个结节: {random_ids}")
        
        # 获取单个结节特征
        if random_ids:
            features = extractor.get_nodule_features(random_ids[0])
            print(f"\n✓ 结节 {random_ids[0]} 特征:")
            for key, value in list(features.items())[:5]:
                print(f"    {key}: {value}")
            print(f"    ... (共 {len(features)} 个特征)")
        
        # 按恶性程度筛选
        high_risk = extractor.get_nodules_by_malignancy(5)
        print(f"\n✓ 高恶性结节(5级): {len(high_risk)} 个")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_matcher():
    """测试RuleMatcher模块"""
    print("\n" + "="*60)
    print("测试 RuleMatcher 模块")
    print("="*60)
    
    try:
        # 初始化
        matcher = RuleMatcher()
        print("✓ 初始化成功")
        
        # 测试恶性风险评估
        test_features = {
            "diameter_mm": 12,
            "texture_score": 4,
            "spiculation_score": 3,
            "malignancy_score": 4
        }
        
        risk = matcher.assess_malignancy_risk(test_features)
        print(f"\n✓ 恶性风险评估:")
        print(f"  - 风险等级: {risk['risk_level']}")
        print(f"  - 恶性评分: {risk['malignancy_score']}")
        print(f"  - 概率: {risk['probability']}")
        print(f"  - 建议: {risk['recommended_action']}")
        
        # 测试Fleischner规则匹配
        plan = matcher.generate_management_plan(test_features)
        print(f"\n✓ Fleischner管理计划:")
        print(f"  - 规则名称: {plan['fleischner_rule']['rule_name']}")
        print(f"  - 管理建议: {plan['management_summary'][:50]}...")
        print(f"  - 随访间隔: {plan['fleischner_rule']['follow_up_months']}个月")
        
        # 测试不同特征
        test_features_low = {
            "diameter_mm": 6,
            "texture_score": 2,
            "spiculation_score": 1,
            "malignancy_score": 2
        }
        
        risk_low = matcher.assess_malignancy_risk(test_features_low)
        print(f"\n✓ 低风险结节评估:")
        print(f"  - 风险等级: {risk_low['risk_level']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration(csv_path: str):
    """测试模块集成"""
    print("\n" + "="*60)
    print("测试模块集成")
    print("="*60)
    
    try:
        # 初始化
        extractor = LIDCExtractor(csv_path)
        matcher = RuleMatcher()
        
        # 获取随机结节
        random_ids = extractor.get_random_nodules(3)
        print(f"随机选取 {len(random_ids)} 个结节进行测试")
        
        results = []
        for nodule_id in random_ids:
            print(f"\n处理结节: {nodule_id}")
            
            # 提取特征
            features = extractor.get_nodule_features(nodule_id)
            
            # 评估风险
            risk = matcher.assess_malignancy_risk(features)
            
            # 生成管理计划
            plan = matcher.generate_management_plan(features)
            
            result = {
                "nodule_id": nodule_id,
                "features": features,
                "risk_assessment": risk,
                "management_plan": plan
            }
            results.append(result)
            
            print(f"  - 风险等级: {risk['risk_level']}")
            print(f"  - 管理建议: {plan['management_summary'][:50]}...")
        
        print(f"\n✓ 成功处理 {len(results)} 个结节")
        return results
        
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Pipeline 功能测试")
    print("="*60)
    
    # 查找LIDC CSV文件
    possible_paths = [
        "data/raw/lidc_nodule_features.csv",
        "../data/raw/lidc_nodule_features.csv",
        "lidc_nodule_features.csv"
    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if not csv_path:
        print("\n✗ 未找到LIDC CSV文件")
        print("请将lidc_nodule_features.csv放在以下位置之一:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\n或者运行时指定路径:")
        print("  python test_pipeline.py <csv_path>")
        
        # 尝试从命令行参数获取
        if len(sys.argv) > 1:
            csv_path = sys.argv[1]
        else:
            return
    
    print(f"\n使用CSV文件: {csv_path}")
    
    # 运行测试
    results = {
        "lidc_extractor": test_lidc_extractor(csv_path),
        "rule_matcher": test_rule_matcher(),
        "integration": test_integration(csv_path) is not None
    }
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for module, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{module}: {status}")
    
    all_passed = all(results.values())
    print(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 存在失败'}")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)