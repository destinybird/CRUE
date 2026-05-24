#!/usr/bin/env python3
"""
sft_build.py  —  基于 clean_data.json 从 sft_data/ 构建 LLaMA-Factory sharegpt 格式训练集
"""

import json
import os
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SFT_DIR = BASE / "output" / "sft_data"
CLEAN_LIST = BASE / "output" / "clean_data.json"
OUT_TRAIN = BASE / "output" / "sft_train.json"
OUT_VAL = BASE / "output" / "sft_val.json"

ROLE_MAP = {"user": "human", "assistant": "gpt"}
VAL_RATIO = 0.05  # 5% 验证集
SEED = 42


def convert_one(filepath: Path) -> dict | None:
    """将单个 sft_data 文件转为 sharegpt 格式"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    convs = data.get("conversations", [])
    if not convs:
        return None

    system_prompt = ""
    messages = []

    for msg in convs:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_prompt = content
        elif role in ROLE_MAP:
            messages.append({"from": ROLE_MAP[role], "value": content})

    if not messages:
        return None

    # 确保以 human 开头、gpt 结尾，且交替出现
    if messages[0]["from"] != "human":
        return None
    if messages[-1]["from"] != "gpt":
        messages = messages[:-1] if len(messages) > 1 else messages

    result = {"conversations": messages}
    if system_prompt:
        result["system"] = system_prompt

    # 保留关键 metadata 便于溯源
    meta = data.get("metadata", {})
    if meta:
        result["metadata"] = {
            "nodule_id": meta.get("nodule_id", ""),
            "patient_id": meta.get("patient_id", ""),
            "risk_level": meta.get("risk_level", ""),
            "source_file": filepath.name,
        }

    return result


def main():
    # 1. 读取 clean 文件名列表
    with open(CLEAN_LIST, "r", encoding="utf-8") as f:
        clean_files = json.load(f)
    print(f"[sft_build] clean 文件数: {len(clean_files)}")

    # 2. 逐个转换
    dataset = []
    skipped = 0
    for fname in clean_files:
        fpath = SFT_DIR / fname
        if not fpath.exists():
            skipped += 1
            continue
        item = convert_one(fpath)
        if item:
            dataset.append(item)
        else:
            skipped += 1

    print(f"[sft_build] 成功转换: {len(dataset)}, 跳过: {skipped}")

    # 3. 打乱并划分 train / val
    random.seed(SEED)
    random.shuffle(dataset)

    val_size = max(1, int(len(dataset) * VAL_RATIO))
    val_set = dataset[:val_size]
    train_set = dataset[val_size:]

    print(f"[sft_build] train: {len(train_set)}, val: {len(val_set)}")

    # 4. 写出
    with open(OUT_TRAIN, "w", encoding="utf-8") as f:
        json.dump(train_set, f, ensure_ascii=False, indent=2)
    with open(OUT_VAL, "w", encoding="utf-8") as f:
        json.dump(val_set, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 训练集: {OUT_TRAIN}  ({len(train_set)} 条)")
    print(f"✅ 验证集: {OUT_VAL}  ({len(val_set)} 条)")

    # 5. 打印样例统计
    if train_set:
        sample = train_set[0]
        n_turns = len(sample["conversations"])
        print(f"\n--- 样例 (第1条) ---")
        print(f"  轮数: {n_turns // 2} 轮对话")
        print(f"  system: {sample.get('system', 'N/A')[:60]}...")
        print(f"  首轮 human: {sample['conversations'][0]['value'][:80]}...")
        print(f"  首轮 gpt:   {sample['conversations'][1]['value'][:80]}...")


if __name__ == "__main__":
    main()