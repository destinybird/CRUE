"""
主数据Pipeline
整合所有模块，实现端到端数据生成
"""

import sys
import os
import json
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lidc_extractor import LIDCExtractor
from clinical_synthesizer import ClinicalSynthesizer
from ebm_engine import generate_ebm_plan
from record_generator import RecordGenerator
from dialog_generator import DialogGenerator
from openai_api import LLMApi


class DataPipeline:
    """数据构建Pipeline"""
    
    def __init__(self, 
                 lidc_csv_path: str,
                 output_dir: str = './output',
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = 'gpt-4'):
        """
        初始化Pipeline
        
        Args:
            lidc_csv_path: LIDC特征CSV路径
            output_dir: 输出目录
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
        """
        # 初始化各模块
        self.lidc_extractor = LIDCExtractor(lidc_csv_path)
        self.llm_client = LLMApi(api_key=api_key, base_url=base_url, model=model)
        self.clinical_synthesizer = ClinicalSynthesizer(self.llm_client)
        self.record_generator = RecordGenerator(self.llm_client)
        self.dialog_generator = DialogGenerator(self.llm_client)
        
        # 输出目录
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'records'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'dialogs'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'features'), exist_ok=True)
    
    def process_nodule(self, nodule_id: str) -> Dict:
        """
        处理单个结节
        
        Args:
            nodule_id: 结节ID
            
        Returns:
            处理结果
        """
        print(f"\n{'='*50}")
        print(f"Processing nodule: {nodule_id}")
        print(f"{'='*50}")
        
        # Step 1: 提取结节特征
        print("\n[Step 1] Extracting nodule features...")
        features = self.lidc_extractor.get_nodule_features(nodule_id)
        print(f"  - Location: {features['location']}")
        print(f"  - Diameter: {features['diameter_mm']}mm")
        print(f"  - Malignancy: {features['malignancy']}")
        
        # Step 2: 生成3个不同患者
        print("\n[Step 2] Synthesizing 3 patient backgrounds...")
        patients = self.clinical_synthesizer.synthesize(features)
        for i, patient in enumerate(patients, 1):
            print(f"  - Patient {i}: {patient.get('age', 'N/A')}岁 {patient.get('gender', 'N/A')}")
        
        # Step 3: EBM规则匹配 (per-patient)
        print("\n[Step 3] Matching EBM rules (per-patient)...")
        management_plans = []
        for i, patient in enumerate(patients, 1):
            plan = generate_ebm_plan(features, patient)
            management_plans.append(plan)
            print(f"  - Patient {i}: {plan['malignancy_risk']['risk_level']}, {len(plan['matched_rules'])} rules matched")
        
        # Step 4: 生成病历
        print("\n[Step 4] Generating medical records...")
        records = self.record_generator.generate_batch(features, patients, management_plans=management_plans)
        print(f"  - Generated {len(records)} records")
        
        # Step 5: 生成对话
        print("\n[Step 5] Generating dialogs...")
        dialogs = self.dialog_generator.generate_batch(records, management_plans)
        print(f"  - Generated {len(dialogs)} dialogs")
        
        # 保存结果
        result = {
            'nodule_id': nodule_id,
            'features': features,
            'patients': patients,
            'management_plans': management_plans,
            'records': records,
            'dialogs': dialogs
        }
        
        self._save_results(result)
        
        return result
    
    def _save_results(self, result: Dict):
        """保存结果到文件"""
        nodule_id = result['nodule_id']
        
        # 保存特征
        features_path = os.path.join(self.output_dir, 'features', f'{nodule_id}.json')
        with open(features_path, 'w', encoding='utf-8') as f:
            json.dump(result['features'], f, ensure_ascii=False, indent=2)
        
        # 保存病历
        for i, record in enumerate(result['records'], 1):
            record_path = os.path.join(self.output_dir, 'records', f'{nodule_id}_patient{i}.txt')
            with open(record_path, 'w', encoding='utf-8') as f:
                f.write(record['full_text'])
        
        # 保存对话
        for i, dialog in enumerate(result['dialogs'], 1):
            dialog_path = os.path.join(self.output_dir, 'dialogs', f'{nodule_id}_patient{i}.json')
            with open(dialog_path, 'w', encoding='utf-8') as f:
                json.dump(dialog, f, ensure_ascii=False, indent=2)
        
        print(f"\n[Saved] Results saved to {self.output_dir}")
    
    def process_batch(self, nodule_ids: List[str]) -> List[Dict]:
        """
        批量处理结节
        
        Args:
            nodule_ids: 结节ID列表
            
        Returns:
            处理结果列表
        """
        results = []
        for nodule_id in nodule_ids:
            try:
                result = self.process_nodule(nodule_id)
                results.append(result)
            except Exception as e:
                print(f"Error processing nodule {nodule_id}: {e}")
        
        return results
    
    def process_random(self, n: int = 5) -> List[Dict]:
        """
        随机处理n个结节
        
        Args:
            n: 结节数量
            
        Returns:
            处理结果列表
        """
        nodule_ids = self.lidc_extractor.get_random_nodules(n)
        return self.process_batch(nodule_ids)


# 使用示例
if __name__ == '__main__':
    # 配置
    LIDC_CSV = '/path/to/lidc_features.csv'
    OUTPUT_DIR = './output'
    
    # 创建pipeline
    pipeline = DataPipeline(
        lidc_csv_path=LIDC_CSV,
        output_dir=OUTPUT_DIR
    )
    
    # 处理单个结节
    result = pipeline.process_nodule('1')
    
    # 或随机处理多个结节
    # results = pipeline.process_random(5)