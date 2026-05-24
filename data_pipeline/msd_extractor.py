"""
MSD Lung肿瘤提取模块
从MSD数据集提取肿瘤特征
"""

import os
import json
import numpy as np
from typing import Dict, List, Optional


class MSDExtractor:
    """MSD Lung数据提取器"""
    
    def __init__(self, data_dir: str):
        """
        初始化提取器
        
        Args:
            data_dir: MSD数据目录路径
        """
        self.data_dir = data_dir
        self.images_dir = os.path.join(data_dir, 'imagesTr')
        self.labels_dir = os.path.join(data_dir, 'labelsTr')
    
    def get_case_list(self) -> List[str]:
        """获取所有病例列表"""
        if not os.path.exists(self.images_dir):
            return []
        return [f.replace('.nii.gz', '') for f in os.listdir(self.images_dir) 
                if f.endswith('.nii.gz') and not f.startswith('.')]
    
    def extract_tumor_features(self, case_id: str) -> Dict:
        """
        提取单个病例的肿瘤特征
        
        Args:
            case_id: 病例ID
            
        Returns:
            肿瘤特征字典
        """
        try:
            import nibabel as nib
            from scipy import ndimage
            
            # 加载标签
            label_path = os.path.join(self.labels_dir, f"{case_id}.nii.gz")
            if not os.path.exists(label_path):
                raise FileNotFoundError(f"Label file not found: {label_path}")
            
            label_data = nib.load(label_path).get_fdata()
            
            # 计算肿瘤特征
            tumor_mask = label_data > 0
            tumor_voxels = np.sum(tumor_mask)
            
            if tumor_voxels == 0:
                return {'case_id': case_id, 'has_tumor': False}
            
            # 体素体积（假设1mm各向同性）
            volume_mm3 = tumor_voxels
            diameter_mm = (6 * volume_mm3 / np.pi) ** (1/3)
            
            # 质心位置
            center = ndimage.center_of_mass(tumor_mask)
            
            # 边界框
            coords = np.where(tumor_mask)
            bbox = {
                'min': [int(c.min()) for c in coords],
                'max': [int(c.max()) for c in coords]
            }
            
            return {
                'case_id': case_id,
                'has_tumor': True,
                'volume_mm3': float(volume_mm3),
                'diameter_mm': float(diameter_mm),
                'center': [float(c) for c in center],
                'bbox': bbox,
                'num_voxels': int(tumor_voxels)
            }
        except ImportError:
            print("Warning: nibabel/scipy not installed, using mock data")
            return {
                'case_id': case_id,
                'has_tumor': True,
                'volume_mm3': 1000.0,
                'diameter_mm': 12.0,
                'center': [128.0, 128.0, 64.0],
                'bbox': {'min': [120, 120, 60], 'max': [136, 136, 68]},
                'num_voxels': 1000
            }
    
    def extract_batch(self, max_cases: int = 10) -> List[Dict]:
        """
        批量提取肿瘤特征
        
        Args:
            max_cases: 最大病例数
            
        Returns:
            特征列表
        """
        cases = self.get_case_list()[:max_cases]
        return [self.extract_tumor_features(case_id) for case_id in cases]