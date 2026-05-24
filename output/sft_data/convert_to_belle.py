import json
import os
from pathlib import Path
from typing import List, Dict, Any

def convert_conversations_to_belle_format(conversations: List[Dict[str, str]]) -> tuple[str, str, str]:
    """
    将conversations格式转换为Belle多轮对话格式
    
    Args:
        conversations: 原始对话列表，包含system, user, assistant角色
        
    Returns:
        (instruction, input, output) 三元组
    """
    if not conversations:
        return "", "", ""
    
    # 构建instruction字段（包含所有历史对话）
    instruction_parts = []
    output = ""
    
    # 遍历对话，构建历史和最后一轮
    for i, turn in enumerate(conversations):
        role = turn.get("role", "")
        content = turn.get("content", "").strip()
        
        if not content:
            continue
            
        if role == "system":
            # system消息也放入instruction开头
            instruction_parts.append(f"System:{content}")
        elif role == "user":
            # 如果不是最后一轮用户消息，就加入instruction
            if i < len(conversations) - 2:  # 还有assistant回复在后面
                instruction_parts.append(f"Human:{content}")
            else:
                # 最后一轮用户消息
                instruction_parts.append(f"Human:{content}")
                # 寻找对应的assistant回复作为output
                if i + 1 < len(conversations) and conversations[i + 1].get("role") == "assistant":
                    output = conversations[i + 1].get("content", "").strip()
        elif role == "assistant":
            # 如果不是最后一轮assistant消息，就加入instruction
            if i < len(conversations) - 1:  # 后面还有对话
                instruction_parts.append(f"Assistant:{content}")
    
    # 拼接instruction
    instruction = "\n".join(instruction_parts)
    
    return instruction, "", output

def process_files(input_dir: str, output_file: str):
    """
    处理目录下所有JSON文件并转换为Belle格式
    
    Args:
        input_dir: 输入目录路径
        output_file: 输出文件路径
    """
    # 处理路径：如果是相对路径，转换为绝对路径
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    
    input_path = input_path.resolve()
    
    print(f"🔍 解析后的输入目录: {input_path}")
    
    if not input_path.exists():
        print(f"❌ 错误：目录 {input_path} 不存在")
        print(f"💡 提示：当前工作目录是 {Path.cwd()}")
        return
    
    if not input_path.is_dir():
        print(f"❌ 错误：{input_path} 不是一个目录")
        return
    
    # 获取所有JSON文件
    json_files = list(input_path.glob("*.json"))
    print(f"📄 找到 {len(json_files)} 个JSON文件")
    
    if len(json_files) == 0:
        print(f"⚠️  警告：目录 {input_path} 中没有找到JSON文件")
        return
    
    processed_count = 0
    skipped_count = 0
    converted_data = []
    skip_reasons = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理单个文件（可能是单个对象或列表）
            items = data if isinstance(data, list) else [data]
            
            for idx, item in enumerate(items):
                # 检查是否包含conversations字段
                if "conversations" not in item:
                    skip_reasons.append(f"{json_file.name}[{idx}]: 缺少conversations字段")
                    skipped_count += 1
                    continue
                
                conversations = item["conversations"]
                if not conversations or not isinstance(conversations, list):
                    skip_reasons.append(f"{json_file.name}[{idx}]: conversations字段为空或格式错误")
                    skipped_count += 1
                    continue
                
                # 转换为Belle格式
                instruction, input_text, output = convert_conversations_to_belle_format(conversations)
                
                if not output:
                    skip_reasons.append(f"{json_file.name}[{idx}]: 无法提取output")
                    skipped_count += 1
                    continue
                
                # 创建Belle格式数据
                belle_item = {
                    "instruction": instruction,
                    "input": input_text,
                    "output": output
                }
                
                converted_data.append(belle_item)
                processed_count += 1
                
        except json.JSONDecodeError as e:
            skip_reasons.append(f"{json_file.name}: JSON解析错误 - {str(e)}")
            skipped_count += 1
        except Exception as e:
            skip_reasons.append(f"{json_file.name}: 处理错误 - {str(e)}")
            skipped_count += 1
    
    # 保存转换后的数据
    if converted_data:
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path = output_path.resolve()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 转换完成！")
        print(f"📊 成功处理: {processed_count} 条对话")
        print(f"⏭️  跳过: {skipped_count} 条对话")
        print(f"💾 输出文件: {output_path}")
        
        # 打印前5个跳过原因（如果有）
        if skip_reasons:
            print(f"\n⚠️  跳过原因（前5条）:")
            for reason in skip_reasons[:5]:
                print(f"  - {reason}")
            if len(skip_reasons) > 5:
                print(f"  ... 还有 {len(skip_reasons) - 5} 条")
    else:
        print("\n❌ 没有成功转换任何数据")

def main():
    # 方式1：使用当前目录（推荐，因为你已经在sft_data目录下了）
    input_dir = "."  # 当前目录
    
    # 方式2：如果你想指定完整路径，取消下面这行的注释
    # input_dir = "/cpfs01/projects-HDD/cfff-0082a359858b_HDD/sxc_22300240012/lung/code_0417/output/sft_data"
    
    output_file = "belle_multiturn_converted.json"
    
    print("🚀 开始转换对话数据...")
    print(f"📁 输入目录: {input_dir}")
    print(f"📄 输出文件: {output_file}")
    print("-" * 50)
    
    process_files(input_dir, output_file)
    
    print("\n✨ 脚本执行完毕！")

if __name__ == "__main__":
    main()