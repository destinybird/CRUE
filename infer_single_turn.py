#!/usr/bin/env python3
"""
infer_single_turn.py - 实验B单轮推理（规则注入版）
"""
import argparse
import json
import os
from vllm import LLM, SamplingParams


def main():
    parser = argparse.ArgumentParser()
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--input", default=os.path.join(base, "data/inputs_with_rules/single_turn_with_rules.jsonl"))
    parser.add_argument("--output", default=os.path.join(base, "data/outputs/expB_single_turn.jsonl"))
    parser.add_argument("--max_tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
    parser.add_argument("--verbose", action="store_true", help="逐条打印推理结果和规则使用情况")
    args = parser.parse_args()

    samples = []
    with open(args.input) as f:
        for line in f:
            samples.append(json.loads(line))
    print(f"加载 {len(samples)} 条单轮样本（含规则注入）")

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

    prompts = []
    for s in samples:
        prompt = tokenizer.apply_chat_template(
            s["messages"], tokenize=False, add_generation_prompt=True
        )
        prompts.append(prompt)

    outputs = llm.generate(prompts, sampling_params)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        for i, (sample, output) in enumerate(zip(samples, outputs)):
            pred_text = output.outputs[0].text
            rule_ids = sample.get("injected_rule_ids", [])
            result = {
                "id": sample["id"],
                "prediction": pred_text,
                "injected_rule_ids": rule_ids,
            }
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            if args.verbose:
                rules_str = ", ".join(rule_ids) if rule_ids else "无"
                preview = pred_text[:80].replace("\n", " ") + ("..." if len(pred_text) > 80 else "")
                print(f"[{i+1}/{len(samples)}] id={sample['id']} | 注入规则: {rules_str} | 生成长度: {len(pred_text)}字符")
                print(f"  预览: {preview}")
    print(f"\n结果保存至 {args.output}")


if __name__ == "__main__":
    main()