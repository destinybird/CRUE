
"""
Feature Translator Module
将LIDC-IDRI数值特征转换为临床描述
"""

import pandas as pd
from typing import Dict, List, Optional


class FeatureTranslator:
    """LIDC特征翻译器：数值→临床描述"""
    
    # 恶性程度映射
    MALIGNANCY_MAP = {
        1: '高度良性',
        2: '可能良性',
        3: '不确定',
        4: '可能恶性',
        5: '高度恶性'
    }
    
    # 毛刺征映射
    SPICULATION_MAP = {
        1: '无毛刺',
        2: '轻微毛刺',
        3: '中等毛刺',
        4: '明显毛刺',
        5: '显著毛刺'
    }
    
    # 分叶征映射
    LOBULATION_MAP = {
        1: '无分叶',
        2: '轻微分叶',
        3: '中等分叶',
        4: '明显分叶',
        5: '显著分叶'
    }
    
    # 边缘特征映射
    MARGIN_MAP = {
        1: '边缘清晰',
        2: '边缘模糊',
        3: '边缘不规则',
        4: '边缘毛糙',
        5: '边缘棘状'
    }
    
    # 纹理/密度映射
    TEXTURE_MAP = {
        1: '磨玻璃',
        2: '混合磨玻璃',
        3: '部分实性',
        4: '实性',
        5: '致密实性'
    }
    
    # 钙化映射
    CALCIFICATION_MAP = {
        1: '无钙化',
        2: '散在钙化',
        3: '偏心钙化',
        4: '中央钙化',
        5: '爆米花样钙化',
        6: '层状钙化'
    }
    
    # 球形度映射
    SPHERICITY_MAP = {
        1: '不规则形',
        2: '椭圆形',
        3: '类圆形',
        4: '圆形',
        5: '球形'
    }
    
    # 结节大小分类
    @staticmethod
    def get_size_category(diameter_mm: float) -> str:
        """根据直径分类结节大小"""
        if diameter_mm < 6:
            return '微小结节(<6mm)'
        elif diameter_mm < 8:
            return '小结节(6-8mm)'
        elif diameter_mm < 30:
            return '结节(8-30mm)'
        else:
            return '肿块(>30mm)'
    
    # 像素转毫米（假设像素间距0.7mm）
    @staticmethod
    def pixels_to_mm(pixels: float, pixel_spacing: float = 0.7) -> float:
        """将像素转换为毫米"""
        return round(pixels * pixel_spacing, 1)
    
    @classmethod
    def translate_feature(cls, feature_name: str, value) -> str:
        """翻译单个特征"""
        maps = {
            'malignancy': cls.MALIGNANCY_MAP,
            'spiculation': cls.SPICULATION_MAP,
            'lobulation': cls.LOBULATION_MAP,
            'margin': cls.MARGIN_MAP,
            'texture': cls.TEXTURE_MAP,
            'calcification': cls.CALCIFICATION_MAP,
            'sphericity': cls.SPHERICITY_MAP
        }
        
        if feature_name in maps:
            mapping = maps[feature_name]
            int_val = int(value) if pd.notna(value) else 3
            return mapping.get(int_val, '不确定')
        return str(value)
    
    @classmethod
    def translate_nodule(cls, nodule: Dict) -> Dict:
        """翻译整个结节数据"""
        # 计算直径(mm)
        diameter_pixels = nodule.get('diameter_pixels', 20)
        diameter_mm = cls.pixels_to_mm(diameter_pixels) if pd.notna(diameter_pixels) else 20.0
        
        # 翻译各特征
        translated = {
            'patient_id': f"LIDC-{nodule.get('patient_folder', '0000')}",
            'nodule_id': nodule.get('nodule_id', 1),
            'diameter_mm': diameter_mm,
            'size_category': cls.get_size_category(diameter_mm),
            'malignancy_desc': cls.translate_feature('malignancy', nodule.get('malignancy', 3)),
            'spiculation_desc': cls.translate_feature('spiculation', nodule.get('spiculation', 1)),
            'lobulation_desc': cls.translate_feature('lobulation', nodule.get('lobulation', 1)),
            'margin_desc': cls.translate_feature('margin', nodule.get('margin', 1)),
            'texture_desc': cls.translate_feature('texture', nodule.get('texture', 4)),
            'calcification_desc': cls.translate_feature('calcification', nodule.get('calcification', 1)),
            'sphericity_desc': cls.translate_feature('sphericity', nodule.get('sphericity', 3)),
            # 原始数值保留
            'malignancy_score': int(nodule.get('malignancy', 3)) if pd.notna(nodule.get('malignancy')) else 3,
            'spiculation_score': int(nodule.get('spiculation', 1)) if pd.notna(nodule.get('spiculation')) else 1,
            'texture_score': int(nodule.get('texture', 4)) if pd.notna(nodule.get('texture')) else 4
        }
        
        return translated
    
    @classmethod
    def generate_clinical_description(cls, translated: Dict) -> str:
        """生成临床描述文本"""
        desc = f"患者肺部发现{translated['size_category']}，"
        desc += f"直径约{translated['diameter_mm']}mm，"
        desc += f"密度呈{translated['texture_desc']}，"
        desc += f"边缘{translated['margin_desc']}，"
        
        if translated['spiculation_desc'] != '无毛刺':
            desc += f"可见{translated['spiculation_desc']}，"
        if translated['lobulation_desc'] != '无分叶':
            desc += f"伴有{translated['lobulation_desc']}，"
        
        desc += f"恶性可能性评估：{translated['malignancy_desc']}。"
        
        return desc


if __name__ == '__main__':
    # 测试
    test_nodule = {
        'patient_folder': 157,
        'nodule_id': 3,
        'malignancy': 4,
        'spiculation': 4,
        'lobulation': 3,
        'margin': 2,
        'texture': 4,
        'calcification': 1,
        'sphericity': 3,
        'diameter_pixels': 33
    }
    
    translator = FeatureTranslator()
    translated = translator.translate_nodule(test_nodule)
    print('翻译结果:')
    for k, v in translated.items():
        print(f'  {k}: {v}')
    
    print("\n临床描述:")
    print(translator.generate_clinical_description(translated))
