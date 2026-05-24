#!/usr/bin/env python3
"""
infer_multi_turn.py - 实验B多轮推理（规则注入版）
"""
import argparse
import json
import os
from collections import defaultdict
from vllm import LLM, SamplingParams


def main():
    parser = argparse.ArgumentParser()
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--input", default=os.path.join(base, "data/inputs_with_rules/multi_turn_with_rules.jsonl"))
    parser.add_argument("--output", default=os.path.join(base, "data/outputs/expB_multi_turn.jsonl"))
    parser.add_argument("--max_tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
    parser.add_argument("--verbose", action="store_true", help="逐条打印推理结果和规则使用情况")
    args = parser.parse_args()

    all_turns = []
    with open(args.input) as f:
        for line in f:
            all_turns.append(json.loads(line))

    groups = defaultdict(list)
    for t in all_turns:
        groups[t["sample_id"]].append(t)
    for sid in groups:
        groups[sid].sort(key=lambda x: x["turn_index"])
    print(f"加载 {len(all_turns)} 条turn, {len(groups)} 个会话")

    llm = LLM(
        model=args.model_path,
        tensor_parallel_size=args.tensor_parallel_size,
        trust_remote_code=True,
    )
    tokenizer = llm.get_tokenizer()
    sampling_params = SamplingParams(
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    results = []
    for sid, turns in groups.items():
        history = []
        for turn in turns:
            if turn["turn_index"] == 0:
                history = list(turn["messages"])
            else:
                user_msgs = [m for m in turn["messages"] if m["role"] == "user"]
                if user_msgs:
                    history.append(user_msgs[-1])

            prompt = tokenizer.apply_chat_template(
                history, tokenize=False, add_generation_prompt=True
            )
            output = llm.generate([prompt], sampling_params)[0]
            pred = output.outputs[0].text

            history.append({"role": "assistant", "content": pred})

            rule_ids = turn.get("injected_rule_ids", [])
            results.append({
                "id": turn["id"],
                "sample_id": sid,
                "turn_index": turn["turn_index"],
                "prediction": pred,
                "injected_rule_ids": rule_ids,
            })

            if args.verbose:
                rules_str = ", ".join(rule_ids) if rule_ids else "无"
                preview = pred[:80].replace("\n", " ") + ("..." if len(pred) > 80 else "")
                print(f"[{len(results)}/{len(all_turns)}] 会话={sid} turn={turn['turn_index']} | 注入规则: {rules_str} | 生成长度: {len(pred)}字符")
                print(f"  预览: {preview}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"结果保存至 {args.output}")


if __name__ == "__main__":
    main()