"""
Main Pipeline Module
主流程模块：整合data_pipeline所有模块，实现完整pipeline
LIDC-IDRI CSV数字 → 临床背景合成 → EBM规则匹配 → 病历生成 → 对话生成
"""
# python main_pipeline.py \  --lidc_csv data/processed/lidc_filtered_balanced.csv \
#   --n_samples 3 \
#   --start_row 0 \
#   --end_row 3 \
#   --output_dir output
  
  
  
  
import sys
import os
import json
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from data_pipeline import (
    LIDCExtractor,
    ClinicalSynthesizer,
    EBMEngine,
    RecordGenerator,
    DialogGenerator
)
from openai_api import LLMApi


class LungAgentPipeline:
    """肺结节Agent数据Pipeline"""
    
    def __init__(self, 
                 lidc_csv_path: str,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 start_row: Optional[int] = None,
                 end_row: Optional[int] = None):
        """
        初始化Pipeline
        
        Args:
            lidc_csv_path: LIDC-IDRI CSV文件路径
            api_key: API密钥（默认使用内置配置）
            base_url: API基础URL（默认使用内置配置）
            model: 模型名称（默认使用内置配置）
            start_row: 起始行号（1-based，包含），None表示从第一行开始
            end_row: 结束行号（1-based，包含），None表示到最后一行
        """
        # API配置（默认值，可通过参数或CLI覆盖）
        API_KEY = "sk-eb47793028590a85c36c6f3e5baa9391e055109c677ebb0e1abab1c2563004dc"  # 替换为你的API密钥
        API_BASE_URL = "https://www.aiwanwu.cc/v1"
        API_MODEL = "gpt-5.4"
        
        # 使用传入参数或默认值
        final_api_key = api_key or API_KEY
        final_base_url = base_url or API_BASE_URL
        final_model = model or API_MODEL
        
        # 初始化LLM客户端
        self.llm_client = LLMApi(
            api_key=final_api_key,
            base_url=final_base_url,
            model=final_model
        )
        
        # 初始化各模块
        self.extractor = LIDCExtractor(lidc_csv_path, start_row=start_row, end_row=end_row)
        self.synthesizer = ClinicalSynthesizer(self.llm_client)
        self.ebm_engine = EBMEngine()
        self.record_generator = RecordGenerator(self.llm_client)
        self.dialog_generator = DialogGenerator(self.llm_client)
        
        # 统计信息
        stats = self.extractor.get_statistics()
        print(f"Pipeline初始化完成:")
        print(f"  - 总结节数: {stats['total_nodules']}")
        print(f"  - 恶性分布: {stats.get('malignancy_dist', 'N/A')}")
    
    def process_nodule(self, nodule_id: str) -> Dict:
        """
        处理单个结节
        
        Args:
            nodule_id: 结节ID
            
        Returns:
            包含所有处理结果的字典
        """
        # Step 1: 提取结节特征
        print(f"\n[Step 1] 提取特征")
        nodule_features = self.extractor.get_nodule_features(nodule_id)
        print(f"  ✓ {nodule_features.get('location', 'N/A')} | {nodule_features.get('diameter_mm', 'N/A')}mm | {nodule_features.get('texture_desc', 'N/A')}")
        
        # Step 2: 合成临床背景（前置，为EBM提供患者信息）
        clinical_context = self.synthesizer.synthesize(nodule_features)
        n_patients = len(clinical_context) if isinstance(clinical_context, list) else 0
        print(f"\n[Step 2] 合成临床背景（{n_patients}个患者）")
        if isinstance(clinical_context, list):
            for _p in clinical_context:
                _pid = _p.get('patient_id', 'N/A')
                _age = _p.get('age', 'N/A')
                _gender = _p.get('gender', 'N/A')
                _smoking = _p.get('smoking_history', 'N/A')
                print(f"  ✓ {_pid}: {_age}岁/{_gender}, {_smoking}")
        
        # Step 3-5: 为每个患者构建PatientState → EBM评估 → 生成病历和对话
        management_plans = []  # 每个患者独立的EBM结果
        risk_assessments = []  # [FIX] 存储每个患者的完整risk_assessment
        dialogs = []
        _ebm_lines = []   # 缓冲EBM结果
        _rec_lines = []   # 缓冲病历结果
        for i, patient in enumerate(clinical_context):
            patient_id = patient.get('patient_id', f'P{i+1:03d}')
            
            # 3a: 构建PatientState字典
            patient_state = self.synthesizer.build_patient_state_dict(
                nodule_features, patient
            )
            
            # 3b: EBM引擎评估
            ebm_result = self.ebm_engine.evaluate(patient_state)
            management_plan = {
                'risk_level': ebm_result.get('risk_level', ''),
                'management_summary': ebm_result.get('management_summary', ''),
                'matched_rules_text': ebm_result.get('matched_rules_text', ''),
                'matched_rules': ebm_result.get('matched_rules', []),
            }
            # [FIX] 构建完整risk_assessment，补充malignancy_score/probability/recommended_action等字段
            _malignancy_risk = ebm_result.get('malignancy_risk', {})
            risk_assessment = {
                'malignancy_score': patient_state.get('malignancy_score', 3),
                'risk_level': ebm_result.get('risk_level', ''),
                'probability': _malignancy_risk.get('probability', 0),
                'recommended_action': ebm_result.get('management_summary', ''),
                'malignancy_probability_pct': round(_malignancy_risk.get('probability', 0) * 100, 2),
                'risk_factors': _malignancy_risk.get('factors', []),
                'protective_factors': [],
            }
            risk_assessments.append(risk_assessment)
            management_plans.append(management_plan)
            _rule_txt = management_plan['matched_rules_text']
            if len(_rule_txt) > 50:
                _rule_txt = _rule_txt[:47] + '...'
            _ebm_lines.append(f"  ✓ {patient_id}: {management_plan['risk_level']} | {_rule_txt}")
            
            # 4: 生成病历
            medical_record = self.record_generator.generate(
                nodule_features=nodule_features,
                clinical_context=[patient],
                risk_assessment=risk_assessment,
                management_plan=management_plan
            )
            patient['full_text'] = medical_record.get('full_text', '')
            
            # 5: 生成对话
            dialog = self.dialog_generator.generate(
                record=medical_record,
                management_plan=management_plan
            )
            dialogs.append(dialog)
            _rec_len = len(medical_record.get('full_text', ''))
            _n_turns = dialog.get('num_turns', 0)
            _rec_lines.append(f"  ✓ {patient_id}: {_rec_len}字符, {_n_turns}轮对话")
        
        # 打印缓冲的EBM和病历结果
        print(f"\n[Step 3] EBM评估")
        for _line in _ebm_lines:
            print(_line)
        print(f"\n[Step 4] 生成病历")
        for _line in _rec_lines:
            print(_line)
        
        # 组装结果（去除子结构中的重复字段）
        nodule_features.pop('nodule_id', None)
        # 取第一个患者的management_plan作为顶层（兼容旧格式）
        top_management = management_plans[0] if management_plans else {}
        result = {
            "nodule_id": nodule_id,
            "nodule_features": nodule_features,
            # "risk_assessment": {'risk_level': top_management.get('risk_level', '')},
            # [FIX] 输出完整risk_assessment，包含validator要求的malignancy_score/probability/recommended_action
            "risk_assessment": risk_assessments[0] if risk_assessments else {'risk_level': top_management.get('risk_level', '')},
            "management_plan": top_management,
            "management_plans": management_plans,
            "clinical_context": clinical_context,
            "dialogs": dialogs
        }
        
        return result
    
    def process_batch(self, 
                      nodule_ids: List[str] = None,
                      n_samples: int = 10,
                      by_malignancy: int = None,
                      save_dir: str = None) -> List[Dict]:
        """
        批量处理结节（支持实时保存）
        
        Args:
            nodule_ids: 指定的结节ID列表
            n_samples: 随机采样数量
            by_malignancy: 按恶性程度筛选（1-5）
            save_dir: 实时保存目录（每处理完一个立即保存）
            
        Returns:
            处理结果列表
        """
        # 获取待处理的数据子集（直接从df取，保留每行唯一的_csv_row）
        if nodule_ids:
            work_df = self.extractor.df[self.extractor.df['nodule_id'].isin(nodule_ids)]
        elif by_malignancy:
            work_df = self.extractor.df[self.extractor.df['malignancy'] == by_malignancy].head(n_samples)
        else:
            work_df = self.extractor.df.head(n_samples)
        
        print(f"\n开始批量处理 {len(work_df)} 个结节...")
        
        # 如果指定了save_dir，创建raw和sft子目录
        if save_dir:
            raw_dir = os.path.join(save_dir, 'raw_results')
            sft_dir = os.path.join(save_dir, 'sft_data')
            os.makedirs(raw_dir, exist_ok=True)
            os.makedirs(sft_dir, exist_ok=True)
        
        # 断点续传：扫描已完成的csv_row行号
        completed_rows = set()
        if save_dir:
            if os.path.exists(raw_dir):
                for fname in os.listdir(raw_dir):
                    if fname.endswith('.json'):
                        # 文件名格式: {csv_row}_{patient_folder}_{xml_file}_{nodule_id}.json
                        try:
                            csv_row_str = fname.split('_', 1)[0]
                            completed_rows.add(int(csv_row_str))
                        except (ValueError, IndexError):
                            pass
            if completed_rows:
                print(f"🔄 断点续传: 检测到 {len(completed_rows)} 个已完成的行，将自动跳过")
        
        # 直接从df遍历构建 (csv_row, nodule_id) 映射，每行有唯一_csv_row
        row_id_pairs = []
        for _, row in work_df.iterrows():
            csv_row = int(row['_csv_row'])
            nid = row['nodule_id']
            row_id_pairs.append((csv_row, nid))
        row_id_pairs.sort(key=lambda x: x[0])  # 按csv_row升序
        
        # 过滤掉已完成的行
        pending_pairs = [(r, nid) for r, nid in row_id_pairs if r not in completed_rows]
        skipped = len(row_id_pairs) - len(pending_pairs)
        if skipped > 0:
            print(f"  ⏭ 跳过 {skipped} 个已完成的行")
        print(f"  📋 待处理: {len(pending_pairs)} 个结节（按CSV行号升序）")
        
        import time as _time
        results = []
        for i, (csv_row, nodule_id) in enumerate(pending_pairs, 1):
            _t0 = _time.time()
            try:
                print(f"\n{'='*50}")
                print(f"[{i}/{len(pending_pairs)}] 结节 {nodule_id} | CSV行 {csv_row}")
                result = self.process_nodule(nodule_id)
                results.append(result)
                _elapsed = _time.time() - _t0
                
                # 实时保存：每处理完一个结节立即保存
                _saved_files = []
                if save_dir:
                    self.save_results([result], raw_dir, verbose=False)
                    self.save_sft_format([result], sft_dir, verbose=False)
                    _nf = result.get('nodule_features', {})
                    _fn = f"{csv_row}_{_nf.get('patient_folder', '')}_{_nf.get('xml_file', '')}_{nodule_id}"
                    _saved_files.append(_fn)
                
                _save_info = f" → {_saved_files[0]}" if _saved_files else ""
                print(f"\n✓ 完成 ({_elapsed:.1f}s){_save_info}")
                    
            except Exception as e:
                _elapsed = _time.time() - _t0
                print(f"\n✗ 失败 ({_elapsed:.1f}s): {e}")
                continue
        
        print(f"\n{'='*50}")
        print(f"批量处理完成: 成功 {len(results)}/{len(pending_pairs)}（跳过已完成 {skipped} 个）")
        
        return results
    
    def save_results(self, results: List[Dict], output_path: str, verbose: bool = True):
        """
        保存处理结果，每个结节单独保存为json文件
        
        Args:
            results: 处理结果列表
            output_path: 输出目录路径
        """
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)
        
        for result in results:
            # 获取命名字段
            nodule_features = result.get('nodule_features', {})
            csv_row = nodule_features.get('csv_row', 0)
            patient_folder = nodule_features.get('patient_folder', 'unknown')
            xml_file = nodule_features.get('xml_file', 'unknown')
            nodule_id = result.get('nodule_id', 'unknown')
            
            # 保存为单独的json文件
            filename = f"{csv_row}_{patient_folder}_{xml_file}_{nodule_id}.json"
            file_path = os.path.join(output_path, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            if verbose:
                print(f"  ✓ 已保存: {filename}")
        
        if verbose:
            print(f"原始结果已保存到目录: {output_path}")
    
    def save_sft_format(self, results: List[Dict], output_path: str, verbose: bool = True):
        """
        保存为SFT训练格式，每个结节单独保存为json文件
        
        Args:
            results: 处理结果列表
            output_path: 输出目录路径
        """
        os.makedirs(output_path, exist_ok=True)
        
        for result in results:
            # 获取patient_folder和nodule_id用于命名
            nodule_features = result.get('nodule_features', {})
            patient_folder = nodule_features.get('patient_folder', 'unknown')
            nodule_id = result.get('nodule_id', 'unknown')
            
            # 获取matched_rules信息（EBM引擎输出）
            management_plan = result.get('management_plan', {})
            matched_rules = management_plan.get('matched_rules', [])
            risk_assessment = result.get('risk_assessment', {})
            
            # 构建诊断依据
            diagnosis_basis = []
            for r in matched_rules:
                diagnosis_basis.append({
                    "rule_id": r.get('rule_id', ''),
                    "category": r.get('category', ''),
                    "condition": r.get('if_condition', ''),
                    "management": r.get('then_action', ''),
                    "evidence_level": r.get('evidence_level', ''),
                    "guideline_source": r.get('guideline_source', '')
                })
            
            # 获取clinical_context和dialogs列表
            clinical_context = result.get('clinical_context', [])
            dialogs = result.get('dialogs', [])
            
            # 为每个患者生成SFT样本
            for i, patient in enumerate(clinical_context):
                patient_id = patient.get('patient_id', f'P{i+1:03d}')
                
                # 获取对应的对话
                dialog = dialogs[i] if i < len(dialogs) else []
                
                # 从dialog中提取turns列表（兼容dict和list两种格式）
                if isinstance(dialog, dict):
                    dialog_turns = dialog.get('turns', [])
                elif isinstance(dialog, list):
                    dialog_turns = dialog
                else:
                    dialog_turns = []
                
                # 构建对话内容
                conversation_content = []
                for turn in dialog_turns:
                    role = turn.get('role', 'unknown')
                    content = turn.get('content', '')
                    if role in ('doctor', 'assistant'):
                        conversation_content.append({
                            "role": "assistant",
                            "content": content
                        })
                    elif role in ('patient', 'user'):
                        conversation_content.append({
                            "role": "user",
                            "content": content
                        })
                
                # 构建丰富的SFT样本
                sft_sample = {
                    "conversations": [
                        {
                            "role": "system",
                            "content": "你是一位资深的肺科医生，擅长肺结节的诊断和管理。请根据Fleischner指南和结节特征提供专业的诊断意见和管理建议。"
                        },
                        {
                            "role": "user",
                            "content": f"请分析以下肺结节并提供诊断意见：\n"
                                       f"- 结节ID: {nodule_id}\n"
                                       f"- 患者ID: {patient_id}\n"
                                       f"- 位置: {nodule_features.get('location', 'N/A')}\n"
                                       f"- 大小: {nodule_features.get('diameter_mm', 'N/A')}mm\n"
                                       f"- 质地: {nodule_features.get('texture_desc', 'N/A')}\n"
                                       f"- 恶性程度评分: {nodule_features.get('malignancy', 'N/A')}/5\n"
                                       f"- 边缘特征: {nodule_features.get('margin_desc', 'N/A')}\n"
                                       f"- 分叶征: {nodule_features.get('lobulation_desc', 'N/A')}\n"
                                       f"- 毛刺征: {nodule_features.get('spiculation_desc', 'N/A')}"
                        },
                        {
                            "role": "assistant",
                            "content": patient.get('full_text', '') if isinstance(patient, dict) else str(patient)
                        }
                    ] + conversation_content,
                    "metadata": {
                        "source": "LIDC-IDRI",
                        "nodule_id": nodule_id,
                        "patient_id": patient_id,
                        "patient_folder": patient_folder,
                        "xml_file": nodule_features.get('xml_file', ''),
                        "risk_level": risk_assessment.get('risk_level', ''),
                        "matched_rules_count": len(matched_rules),
                        "diagnosis_basis": diagnosis_basis,
                        "management_summary": management_plan.get('management_summary', ''),
                        "matched_rules_text": management_plan.get('matched_rules_text', '')
                    }
                }
                
                # 保存为单独的json文件
                csv_row = nodule_features.get('csv_row', 0)
                xml_file = nodule_features.get('xml_file', 'unknown')
                filename = f"{csv_row}_{patient_folder}_{xml_file}_{nodule_id}_{patient_id}.json"
                file_path = os.path.join(output_path, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(sft_sample, f, ensure_ascii=False, indent=2)
                
                if verbose:
                    print(f"  ✓ 已保存: {filename}")
        
        if verbose:
            print(f"\nSFT格式数据已保存到目录: {output_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='肺结节Agent数据Pipeline')
    parser.add_argument('--lidc_csv', type=str, required=True, help='LIDC-IDRI CSV文件路径')
    parser.add_argument('--api_key', type=str, default=None, help='需要修改成你的key')
    parser.add_argument('--base_url', type=str, default=None, help='需要修改成你的URL')
    parser.add_argument('--model', type=str, default='gpt-5.4', help='模型名称')
    parser.add_argument('--n_samples', type=int, default=10, help='处理样本数量')
    parser.add_argument('--output_dir', type=str, default='output', help='输出目录')
    parser.add_argument('--start_row', type=int, default=None, help='起始行号（1-based，包含）')
    parser.add_argument('--end_row', type=int, default=None, help='结束行号（1-based，包含）')
    
    args = parser.parse_args()
    
    # [FIX] 将output_dir解析为相对于脚本所在目录的绝对路径，避免cwd不同导致断点续传失效
    if not os.path.isabs(args.output_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.output_dir = os.path.join(script_dir, args.output_dir)
    
    # 初始化Pipeline
    pipeline = LungAgentPipeline(
        lidc_csv_path=args.lidc_csv,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        start_row=args.start_row,
        end_row=args.end_row
    )
    
    # 批量处理（实时保存，每处理完一个结节立即写入磁盘）
    results = pipeline.process_batch(
        n_samples=args.n_samples,
        save_dir=args.output_dir
    )
    
    print(f"\n✅ 所有数据已实时保存到: {args.output_dir}")
    print(f"  - 原始结果: {args.output_dir}/raw_results/")
    print(f"  - SFT数据:  {args.output_dir}/sft_data/")


if __name__ == '__main__':
    main()