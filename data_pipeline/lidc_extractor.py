"""
LIDC-IDRI特征提取模块
从CSV文件提取肺结节特征
"""

import pandas as pd
import math
from typing import Dict, List, Optional


def _safe_int(val, default=3):
    """NaN安全的int转换"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return int(val)

def _safe_float(val, default=10.0):
    """NaN安全的float转换"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return float(val)

# LIDC texture 1-5 → 中文描述
TEXTURE_DESC_MAP = {
    1: "纯磨玻璃",
    2: "磨玻璃为主",
    3: "混合密度（部分实性）",
    4: "实性为主",
    5: "完全实性",
}


class LIDCExtractor:
    """LIDC-IDRI数据提取器"""
    
    def __init__(self, csv_path: str, start_row: int = None, end_row: int = None):
        """
        初始化提取器
        
        Args:
            csv_path: LIDC特征CSV文件路径
            start_row: 起始行号（1-based，包含），None表示从第一行开始
            end_row: 结束行号（1-based，包含），None表示到最后一行
        """
        self.csv_path = csv_path
        self.start_row = start_row
        self.end_row = end_row
        self.df = pd.read_csv(csv_path)
        self._preprocess()
    
    def _preprocess(self):
        """数据预处理"""
        # 标准化列名
        self.df.columns = [col.strip().lower().replace(' ', '_') for col in self.df.columns]
        
        # 保留原始CSV行号（1-based，不含表头）
        self.df['_csv_row'] = self.df.index + 1
        
        # 确保必要的列存在
        required_cols = ['nodule_id', 'malignancy', 'texture', 'calcification', 
                        'margin', 'sphericity', 'lobulation', 'spiculation']
        for col in required_cols:
            if col not in self.df.columns:
                # 尝试找到匹配的列
                for actual_col in self.df.columns:
                    if col in actual_col:
                        self.df[col] = self.df[actual_col]
                        break
        
        # 根据行范围过滤数据（行号从1开始，不包括表头）
        if self.start_row is not None or self.end_row is not None:
            start_idx = (self.start_row - 1) if self.start_row is not None else 0
            end_idx = self.end_row if self.end_row is not None else len(self.df)
            
            # 确保索引有效
            start_idx = max(0, start_idx)
            end_idx = min(len(self.df), end_idx)
            
            if start_idx >= end_idx:
                raise ValueError(f"Invalid row range: start_row={self.start_row}, end_row={self.end_row}")
            
            self.df = self.df.iloc[start_idx:end_idx].reset_index(drop=True)
            print(f"已过滤数据行范围: {self.start_row or 1} 到 {self.end_row or '末尾'}，共 {len(self.df)} 条数据")
    
    def get_nodule_features(self, nodule_id: str) -> Dict:
        """
        获取单个结节的特征
        
        Args:
            nodule_id: 结节ID
            
        Returns:
            结节特征字典
        """
        row = self.df[self.df['nodule_id'].astype(str) == str(nodule_id)]
        if row.empty:
            raise ValueError(f"Nodule {nodule_id} not found")
        
        row = row.iloc[0]
        return {
            'nodule_id': str(nodule_id),
            'patient_folder': str(row.get('patient_folder', '')),
            'xml_file': str(row.get('xml_file', '')),
            'malignancy': _safe_int(row.get('malignancy'), 3),
            'texture': _safe_int(row.get('texture'), 3),
            'calcification': _safe_int(row.get('calcification'), 6),
            'margin': _safe_int(row.get('margin'), 3),
            'sphericity': _safe_int(row.get('sphericity'), 3),
            'lobulation': _safe_int(row.get('lobulation'), 3),
            'spiculation': _safe_int(row.get('spiculation'), 3),
            'diameter_mm': _safe_float(row.get('diameter_mm'), 10.0),
            'subtlety': _safe_int(row.get('subtlety'), 3),
            'location': row.get('location', '右肺上叶'),
            'csv_row': int(row.get('_csv_row', 0)),
            'texture_desc': TEXTURE_DESC_MAP.get(_safe_int(row.get('texture'), 3), '实性'),
        }
    
    def get_all_nodule_ids(self) -> List[str]:
        """获取所有结节ID"""
        return self.df['nodule_id'].astype(str).tolist()
    
    def get_nodules_by_malignancy(self, min_score: int = 4) -> List[str]:
        """根据恶性程度筛选结节"""
        filtered = self.df[self.df['malignancy'] >= min_score]
        return filtered['nodule_id'].astype(str).tolist()
    
    def get_random_nodules(self, n: int = 10) -> List[str]:
        """随机获取n个结节"""
        sample = self.df.sample(min(n, len(self.df)))
        return sample['nodule_id'].astype(str).tolist()
    
    def get_statistics(self) -> Dict:
        """获取数据集统计信息"""
        return {
            'total_nodules': len(self.df),
            'malignancy_dist': self.df['malignancy'].value_counts().to_dict(),
            'texture_dist': self.df['texture'].value_counts().to_dict(),
            'avg_diameter': self.df['diameter_mm'].mean() if 'diameter_mm' in self.df.columns else None
        }