"""
EBM规则匹配模块
根据结节特征匹配临床指南规则
支持从xlsx加载完整EBM规则（NSCLC_v3等），也保留硬编码fallback
"""

import math
import re
from typing import Dict, List, Optional, Tuple

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class RuleMatcher:
    """循证医学规则匹配器"""
    
    # LIDC texture → density 映射
    TEXTURE_TO_DENSITY = {
        1: 'ground_glass',   # Non-Solid / GGO
        2: 'ground_glass',   # Non-Solid / GGO
        3: 'part_solid',     # Part Solid
        4: 'solid',          # Solid
        5: 'solid',          # Solid
    }
    
    # LIDC malignancy → risk 映射
    MALIGNANCY_TO_RISK = {
        1: 'low',
        2: 'low',
        3: 'medium',
        4: 'high',
        5: 'high',
    }
    
    # 恶性风险评估规则（与CSV risk_level保持一致：低危/中危/高危）
    MALIGNANCY_RISK = {
        0: {'level': '低危', 'probability': '<1%', 'action': '年度随访'},
        1: {'level': '低危', 'probability': '<5%', 'action': '年度随访'},
        2: {'level': '低危', 'probability': '1-5%', 'action': '6-12个月随访'},
        3: {'level': '中危', 'probability': '5-65%', 'action': 'PET-CT或活检'},
        4: {'level': '高危', 'probability': '65-90%', 'action': '考虑手术切除'},
        5: {'level': '高危', 'probability': '>90%', 'action': '建议手术切除'},
    }
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        初始化规则匹配器
        
        Args:
            rules_path: xlsx规则文件路径，None则使用硬编码fallback
        """
        self.xlsx_rules = []
        self.rules_path = rules_path
        
        if rules_path and HAS_PANDAS:
            try:
                df = pd.read_excel(rules_path, header=0)
                self.xlsx_rules = self._parse_xlsx_rules(df)
                print(f"  [RuleMatcher] 已加载 {len(self.xlsx_rules)} 条EBM规则 ({rules_path})")
            except Exception as e:
                print(f"  [RuleMatcher] xlsx规则加载失败: {e}，将使用硬编码fallback")
    
    # ==================== xlsx规则解析 ====================
    
    def _parse_xlsx_rules(self, df) -> List[Dict]:
        """解析xlsx规则为结构化格式"""
        rules = []
        for _, row in df.iterrows():
            rule = {
                'id': row.iloc[0],
                'if_condition': str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                'then_action': str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
                'variables': str(row.iloc[3]).split('; ') if pd.notna(row.iloc[3]) else [],
            }
            rules.append(rule)
        return rules
    
    # ==================== NLP条件提取（来自src版） ====================
    
    def _extract_size_range(self, condition: str) -> Tuple[Optional[float], Optional[float]]:
        """从条件文本中提取大小范围"""
        if '小于' in condition and 'mm' in condition:
            match = re.search(r'小于(\d+)\s*mm', condition)
            if match:
                return (0, float(match.group(1)))
        if '大于' in condition and 'mm' in condition:
            match = re.search(r'大于(?:或等于)?(\d+)\s*mm', condition)
            if match:
                return (float(match.group(1)), float('inf'))
        match = re.search(r'(\d+)[–\-](\d+)\s*mm', condition)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        return (None, None)
    
    def _extract_density(self, condition: str) -> Optional[str]:
        """从条件文本中提取密度类型"""
        if '部分实性' in condition or '混合' in condition:
            return 'part_solid'
        if '非实性' in condition or '磨玻璃' in condition:
            return 'ground_glass'
        if '实性' in condition:
            return 'solid'
        return None
    
    def _extract_risk(self, condition: str) -> Optional[str]:
        """从条件文本中提取风险等级"""
        if '风险低' in condition:
            return 'low'
        if '风险高' in condition:
            return 'high'
        return None
    
    def _extract_nodule_count(self, condition: str) -> Optional[str]:
        """从条件文本中提取结节数量"""
        if '单发' in condition:
            return 'single'
        if '多发' in condition:
            return 'multiple'
        return None
    
    # ==================== 三层匹配（来自src版） ====================
    
    def _match_xlsx_rules(self, patient_state: Dict) -> List[Dict]:
        """用三层匹配策略匹配xlsx规则"""
        matched = []
        diameter_mm = patient_state.get('diameter_mm', 20)
        density = patient_state.get('density', 'solid')
        risk = patient_state.get('risk', 'high')
        nodule_count = patient_state.get('nodule_count', 'single')
        
        for rule in self.xlsx_rules:
            condition = rule['if_condition']
            score = 0
            total_checks = 0
            
            # Layer 1: 大小匹配（权重2x，size是最关键的分层维度）
            min_size, max_size = self._extract_size_range(condition)
            if min_size is not None and max_size is not None:
                total_checks += 2
                if min_size <= diameter_mm < max_size:
                    score += 2
            
            # Layer 2: 密度匹配
            rule_density = self._extract_density(condition)
            if rule_density:
                total_checks += 1
                if rule_density == density:
                    score += 1
            
            # Layer 3: 风险/数量匹配
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
            
            if total_checks > 0 and score / total_checks >= 0.75:
                matched.append({
                    'rule': rule,
                    'match_score': score / total_checks,
                })
        
        matched.sort(key=lambda x: x['match_score'], reverse=True)
        return matched
    
    def _chain_related_rules(self, patient_state: Dict, primary_matches: List[Dict]) -> List[Dict]:
        """根据结节特征推导关联的临床流程规则（检查、分期、治疗等）"""
        chained = []
        matched_ids = {item['rule']['id'] for item in primary_matches}
        
        diameter_mm = patient_state.get('diameter_mm', 20)
        risk = patient_state.get('risk', 'high')
        
        is_large = diameter_mm > 8
        is_high_risk = risk == 'high'
        needs_staging = is_large or (6 <= diameter_mm <= 8 and is_high_risk)
        
        # 规则链定义：(触发条件, 关联规则ID列表, 推导原因)
        chains = [
            (True,           ['R-EXAM-01', 'R-EXAM-02'],   '发现肺结节，需初始评估'),
            (needs_staging,  ['R-EXAM-03', 'R-EXAM-04'],   '结节需进一步分期评估'),
            (is_large,       ['R-NODULE-12', 'R-NODULE-13'], '大结节需评估治疗路径'),
        ]
        
        rule_index = {r['id']: r for r in self.xlsx_rules}
        
        for condition, rule_ids, reason in chains:
            if not condition:
                continue
            for rid in rule_ids:
                if rid in matched_ids or rid not in rule_index:
                    continue
                chained.append({
                    'rule': rule_index[rid],
                    'match_score': 0.5,
                    'chain_reason': reason,
                })
                matched_ids.add(rid)
        
        return chained
    
    def _lidc_to_patient_state(self, features: Dict) -> Dict:
        """将LIDC结节特征转换为xlsx匹配所需的patient_state"""
        texture = features.get('texture', 3)
        malignancy = features.get('malignancy', 3)
        return {
            'diameter_mm': features.get('diameter_mm', 20),
            'density': self.TEXTURE_TO_DENSITY.get(texture, 'solid'),
            'risk': self.MALIGNANCY_TO_RISK.get(malignancy, 'medium'),
            'nodule_count': 'single',  # LIDC默认单发
        }
    
    # ==================== 公共API（保持兼容） ====================
    
    def assess_malignancy_risk(self, features: Dict) -> Dict:
        """评估恶性风险，根据形态学特征细化概率区间"""
        malignancy_score = features.get('malignancy', 3)
        risk_info = self.MALIGNANCY_RISK.get(malignancy_score, self.MALIGNANCY_RISK[3])
        
        risk_factors = []
        protective_factors = []
        
        if features.get('spiculation', 3) >= 4:
            risk_factors.append('毛刺征阳性')
        if features.get('lobulation', 3) >= 4:
            risk_factors.append('分叶征阳性')
        if features.get('calcification', 6) in [1, 2, 3]:
            protective_factors.append('钙化存在')
        if features.get('sphericity', 3) >= 4:
            protective_factors.append('形态规则')
        
        # --- 基于 logistic 映射计算恶性概率 ---
        prob_pct = self._compute_malignancy_probability(features)
        prob_str = f"约{prob_pct}%"
        
        return {
            'malignancy_score': malignancy_score,
            'risk_level': risk_info['level'],
            'probability': prob_str,
            'malignancy_probability_pct': prob_pct,   # 数值型，供下游使用
            'recommended_action': risk_info['action'],
            'risk_factors': risk_factors,
            'protective_factors': protective_factors,
        }
    
    @staticmethod
    def _compute_malignancy_probability(features: Dict) -> float:
        """
        基于 LIDC 专家共识评分的 logistic 概率映射。

        模型:  logit(p) = α × malignancy_score + β + Σ(feature_adj)
        然后  p = sigmoid(logit)

        参数选择依据
        ─────────────
        • α=1.5, β=−5.2 使 score 1→~2.4%, 3→~33%, 5→~91%
          与 LIDC 标注语义（1=极不可能, 5=极可能）对齐。
        • 影像特征权重参考 Brock / Lung-RADS 中各征象的
          效应量级（OR 约 1.5-2.0），在 logit 尺度上取
          保守值 0.3-0.7。
        • 直径调节 0.04/mm 对应 OR≈1.04/mm，与 Brock 模型
          中直径系数量级一致。

        Returns
        -------
        float : 恶性概率百分比，保留一位小数，范围 [1.0, 99.0]
        """
        score = features.get('malignancy', 3)
        ALPHA, BETA = 1.5, -5.2
        logit = ALPHA * score + BETA

        # ---- 影像形态学特征调节（logit 尺度） ----
        spiculation  = features.get('spiculation', 3)
        lobulation   = features.get('lobulation', 3)
        calcification = features.get('calcification', 6)   # 6=absent
        sphericity   = features.get('sphericity', 3)
        diameter     = features.get('diameter_mm', 8.0)

        if spiculation >= 4:          # 毛刺征阳性
            logit += 0.5
        if lobulation >= 4:           # 分叶征阳性
            logit += 0.3
        if calcification in (1, 2, 3):  # 良性钙化模式
            logit -= 0.7
        if sphericity >= 4:           # 形态规则（偏良性）
            logit -= 0.3

        # 直径调节：>6 mm 每增 1 mm logit +0.04，上限 cap 25 mm 增量
        if diameter > 6:
            logit += 0.04 * min(diameter - 6, 25)

        # ---- sigmoid → 概率 ----
        prob = 1.0 / (1.0 + math.exp(-logit))
        prob = max(0.01, min(0.99, prob))       # clamp [1%, 99%]
        return round(prob * 100, 1)
    
    def generate_management_plan(self, features: Dict) -> Dict:
        """
        生成管理计划
        优先使用xlsx规则匹配，无xlsx时fallback到硬编码
        """
        risk = self.assess_malignancy_risk(features)
        
        # 尝试xlsx匹配
        if self.xlsx_rules:
            patient_state = self._lidc_to_patient_state(features)
            primary = self._match_xlsx_rules(patient_state)
            chained = self._chain_related_rules(patient_state, primary)
            
            all_matched = primary + chained
            if all_matched:
                # primary取top-3，chain全部保留，合计上限8条
                top_primary = primary[:3]
                all_rules = top_primary + chained
                all_rules = all_rules[:8]
                
                rules_text_parts = []
                recommendations = []
                for item in all_rules:
                    r = item['rule']
                    reason = item.get('chain_reason', '')
                    if reason:
                        rules_text_parts.append(
                            f"[{r['id']}] (关联推导: {reason}) {r['if_condition']}"
                        )
                    else:
                        rules_text_parts.append(
                            f"[{r['id']}] (匹配度{item['match_score']:.0%}) {r['if_condition']}"
                        )
                    recommendations.append(f"[{r['id']}] {r['then_action']}")
                
                matched_rules_text = '\n'.join(rules_text_parts)
                management_summary = '；'.join(recommendations[:4])
                
                return {
                    'matched_rules_text': matched_rules_text,
                    'matched_rules_count': len(all_rules),
                    'top_rules': all_rules,
                    'management_summary': f"EBM规则匹配({len(all_matched)}条)：{management_summary}",
                }
        
        # Fallback: 硬编码逻辑
        return self._fallback_management_plan(features, risk)
    
    def _fallback_management_plan(self, features: Dict, risk: Dict) -> Dict:
        """硬编码fallback（原有逻辑）"""
        texture = features.get('texture', 3)
        diameter = features.get('diameter_mm', 0)
        
        if texture >= 4 and diameter >= 8:
            desc = '较大实性结节，建议PET-CT或活检，3个月随访'
        elif texture >= 4:
            desc = '孤立性实性结节，低风险6-12个月随访CT'
        elif texture <= 2:
            desc = '纯磨玻璃结节，6-12个月随访，持续存在则年度随访'
        else:
            desc = '部分实性结节，3-6个月随访，实性成分>5mm考虑手术'
        
        return {
            'matched_rules_text': f"[Fleischner硬编码] {desc}",
            'matched_rules_count': 1,
            'top_rules': [],
            'management_summary': f"{desc}。恶性风险：{risk['risk_level']}（{risk['probability']}），"
                                  f"建议{risk['recommended_action']}。",
        }