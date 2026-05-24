"""
多轮对话生成模块
基于病历生成医患多轮对话
"""

import sys
import os
import json
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, List, Optional
from openai_api import LLMApi
from prompts import DIALOG_GENERATION_PROMPT


class DialogGenerator:
    """医患对话生成器"""
    
    def __init__(self, llm_client: LLMApi = None, num_turns: int = 5):
        """
        初始化生成器
        
        Args:
            llm_client: LLM API客户端
            num_turns: 对话轮数
        """
        self.llm_client = llm_client or LLMApi()
        self.num_turns = num_turns
    
    def generate(self, record: Dict, management_plan: Dict) -> Dict:
        """
        生成单个对话
        
        Args:
            record: 病历数据
            management_plan: 管理计划
            
        Returns:
            对话数据
        """
        # 准备prompt参数
        prompt_params = {
            'medical_record_text': record.get('full_text', ''),
            'age': record.get('age', 'N/A'),
            'gender': record.get('gender', 'N/A'),
            'smoking_history': record.get('smoking_history', 'N/A'),
            # EBM循证医学规则注入
            'risk_level': management_plan.get('risk_level', '未评估'),
            'management_summary': management_plan.get('management_summary', '暂无'),
            'matched_rules_text': management_plan.get('matched_rules_text', '暂无匹配规则')
        }
        
        user_prompt = DIALOG_GENERATION_PROMPT.format(**prompt_params)
        
        # 调用LLM生成对话
        dialog_text = self.llm_client.call(
            system_prompt="你是一位医学对话模拟专家，擅长生成真实自然的医患对话。",
            user_prompt=user_prompt,
            temperature=0.7
        )
        
        # 解析对话为结构化格式
        dialog_turns = self._parse_dialog(dialog_text)
        
        return {
            'patient_id': record.get('patient_id', 'N/A'),
            'turns': dialog_turns,
            'num_turns': len(dialog_turns)
        }
    
    def _parse_dialog(self, dialog_text: str) -> List[Dict]:
        """
        解析对话文本为结构化格式
        支持两种格式：
        1. JSON格式: [{"role": "user/assistant", "content": "..."}]
        2. 文本格式: 医生：.../患者：...
        
        Args:
            dialog_text: 对话文本
            
        Returns:
            对话轮次列表
        """
        # 优先尝试JSON解析
        turns = self._try_parse_json(dialog_text)
        if turns:
            return turns
        
        # 回退到文本行解析
        return self._parse_text_lines(dialog_text)
    
    def _try_parse_json(self, dialog_text: str) -> List[Dict]:
        """尝试从对话文本中解析JSON格式"""
        text = dialog_text.strip()
        
        # 去除markdown代码块标记
        pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        
        # 尝试直接解析JSON数组
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return self._normalize_json_turns(data)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 尝试找到JSON数组部分 (可能前后有额外文本)
        bracket_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if bracket_match:
            try:
                data = json.loads(bracket_match.group())
                if isinstance(data, list):
                    return self._normalize_json_turns(data)
            except (json.JSONDecodeError, ValueError):
                pass
        
        return []
    
    def _normalize_json_turns(self, data: List[Dict]) -> List[Dict]:
        """将JSON对话数据标准化为统一格式"""
        turns = []
        role_map = {
            'user': 'patient',
            'patient': 'patient',
            'assistant': 'doctor',
            'doctor': 'doctor',
            '患者': 'patient',
            '医生': 'doctor'
        }
        for item in data:
            if not isinstance(item, dict):
                continue
            role = item.get('role', '').lower().strip()
            content = item.get('content', '').strip()
            mapped_role = role_map.get(role)
            if mapped_role and content:
                turns.append({
                    'role': mapped_role,
                    'content': content
                })
        return turns
    
    def _parse_text_lines(self, dialog_text: str) -> List[Dict]:
        """按行解析文本格式的对话"""
        turns = []
        lines = dialog_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('医生') or line.startswith('Doctor') or line.startswith('D:'):
                role = 'doctor'
                content = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif line.startswith('患者') or line.startswith('Patient') or line.startswith('P:'):
                role = 'patient'
                content = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            else:
                continue
            
            if content:
                turns.append({
                    'role': role,
                    'content': content
                })
        
        return turns
    
    def generate_batch(self, records: List[Dict], management_plans: List[Dict]) -> List[Dict]:
        """
        批量生成对话
        
        Args:
            records: 病历列表
            management_plans: 管理计划列表
            
        Returns:
            对话列表
        """
        dialogs = []
        for record, plan in zip(records, management_plans):
            try:
                dialog = self.generate(record, plan)
                dialogs.append(dialog)
            except Exception as e:
                print(f"Error generating dialog for patient {record.get('patient_id')}: {e}")
        
        return dialogs