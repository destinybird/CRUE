
"""
Rule Matcher Module
EBM规则匹配模块：三层匹配策略
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple


class RuleMatcher:
    """EBM规则匹配器"""
    
    def __init__(self, rules_path: str):
        """初始化规则匹配器"""
        self.rules_df = pd.read_excel(rules_path, header=1)
        self.rules = self._parse_rules()
    
    def _parse_rules(self) -> List[Dict]:
        """解析规则为结构化格式"""
        rules = []
        for _, row in self.rules_df.iterrows():
            rule = {
                'id': row.iloc[0],
                'if_condition': row.iloc[1],
                'then_action': row.iloc[2],
                'variables': row.iloc[3].split('; ') if pd.notna(row.iloc[3]) else [],
                'source': row.iloc[4] if pd.notna(row.iloc[4]) else ''
            }
            rules.append(rule)
        return rules
    
    def _extract_size_range(self, condition: str) -> Tuple[Optional[float], Optional[float]]:
        """从条件中提取大小范围"""
        if '小于' in condition and 'mm' in condition:
            match = re.search(r'小于(\d+)\s*mm', condition)
            if match:
                return (0, float(match.group(1)))
        
        if '大于' in condition and 'mm' in condition:
            match = re.search(r'大于(\d+)\s*mm', condition)
            if match:
                return (float(match.group(1)), float('inf'))
        
        match = re.search(r'(\d+)[–\-](\d+)\s*mm', condition)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        
        return (None, None)
    
    def _extract_density(self, condition: str) -> Optional[str]:
        """从条件中提取密度类型"""
        if '实性' in condition and '部分' not in condition and '磨玻璃' not in condition:
            return 'solid'
        if '磨玻璃' in condition:
            return 'ground_glass'
        if '部分实性' in condition or '混合' in condition:
            return 'part_solid'
        return None
    
    def _extract_risk(self, condition: str) -> Optional[str]:
        """从条件中提取风险等级"""
        if '风险低' in condition:
            return 'low'
        if '风险高' in condition:
            return 'high'
        return None
    
    def _extract_nodule_count(self, condition: str) -> Optional[str]:
        """从条件中提取结节数量"""
        if '单发' in condition:
            return 'single'
        if '多发' in condition:
            return 'multiple'
        return None
    
    def match_rule(self, patient_state: Dict) -> List[Dict]:
        """匹配患者状态与规则"""
        matched_rules = []
        
        diameter_mm = patient_state.get('diameter_mm', 20)
        density = patient_state.get('density', 'solid')
        risk = patient_state.get('risk', 'high')
        nodule_count = patient_state.get('nodule_count', 'single')
        
        for rule in self.rules:
            condition = rule['if_condition']
            score = 0
            total_checks = 0
            
            min_size, max_size = self._extract_size_range(condition)
            if min_size is not None and max_size is not None:
                total_checks += 1
                if min_size <= diameter_mm < max_size:
                    score += 1
            
            rule_density = self._extract_density(condition)
            if rule_density:
                total_checks += 1
                if rule_density == density:
                    score += 1
            
            rule_risk = self._extract_risk(condition)
            if rule_risk:
                total_checks += 1
                if rule_risk == risk:
                    score += 1
            
            rule_count = self._extract_nodule_count(condition)
            if rule_count:
                total_checks += 1
                if rule_count == nodule_count:
                    score += 1
            
            if total_checks > 0:
                match_ratio = score / total_checks
                if match_ratio >= 0.75:
                    matched_rules.append({
                        'rule': rule,
                        'match_score': match_ratio,
                        'matched_checks': score,
                        'total_checks': total_checks
                    })
        
        matched_rules.sort(key=lambda x: x['match_score'], reverse=True)
        return matched_rules
    
    def get_recommendations(self, matched_rules: List[Dict]) -> List[str]:
        """从匹配规则中提取推荐建议"""
        recommendations = []
        for item in matched_rules:
            rule = item['rule']
            action = rule['then_action']
            recommendations.append(f"[{rule['id']}] {action}")
        return recommendations


if __name__ == '__main__':
    matcher = RuleMatcher('/Users/yixuanli/Downloads/LUNG_papers/code/data/rules/NSCLC_v3.xlsx')
    
    test_patient = {
        'diameter_mm': 18.5,
        'density': 'solid',
        'risk': 'high',
        'nodule_count': 'single'
    }
    
    matched = matcher.match_rule(test_patient)
    print(f'匹配到 {len(matched)} 条规则:')
    for item in matched:
        print(f"  {item['rule']['id']}: {item['rule']['if_condition']}")
        print(f"    匹配度: {item['match_score']:.2f}")
        print(f"    建议: {item['rule']['then_action'][:50]}...")
