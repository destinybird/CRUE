#!/usr/bin/env python3
"""
eval_single_turn.py - 实验B单轮评估

指标:
  1. Rule Recall
  2. Rule Precision
  3. Rule F1
  4. ROUGE-L

用法:
    python eval_single_turn.py \
        --predictions ../../data/outputs/expB_single_turn.jsonl \
        --ground_truth ../../data/ground_truth/single_turn_gt.jsonl \
        --ebm_rules ../../data/rules/ebm.xlsx \
        --output ../../data/results/expB_single_turn_metrics.json
"""
import argparse
import json
import os
from tqdm import tqdm
from eval_utils_rules import (
    load_ebm_rules, evaluate_single_sample, aggregate_metrics
)


def main():
    parser = argparse.ArgumentParser()
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--ground_truth", default=os.path.join(base, "data/ground_truth/single_turn_gt.jsonl"))
    parser.add_argument("--ebm_rules", default=os.path.join(base, "data/rules/ebm.xlsx"))
    parser.add_argument("--output", default=os.path.join(base, "data/results/expB_single_turn_metrics.json"))
    parser.add_argument("--save_details", action="store_true", help="保存逐样本详细结果")
    args = parser.parse_args()

    # 加载
    ebm_rules = load_ebm_rules(args.ebm_rules)
    print(f"EBM规则: {len(ebm_rules)} 条")

    preds = {}
    with open(args.predictions) as f:
        for line in f:
            item = json.loads(line)
            preds[item["id"]] = item

    gts = {}
    with open(args.ground_truth) as f:
        for line in f:
            item = json.loads(line)
            gts[item["id"]] = item

    # 逐样本评估
    sample_metrics = []
    details = []
    matched_ids = set(preds.keys()) & set(gts.keys())
    print(f"匹配样本: {len(matched_ids)}/{len(preds)}")

    for sid in tqdm(sorted(matched_ids), desc="评估中"):
        pred = preds[sid]["prediction"]
        gt = gts[sid]
        ref = gt.get("reference_response", "")
        rules_text = gt.get("matched_rules_text", "")

        metrics = evaluate_single_sample(pred, ref, rules_text, ebm_rules)
        metrics["id"] = sid
        sample_metrics.append(metrics)

        if args.save_details:
            details.append(metrics)

    # 汇总
    agg = aggregate_metrics(sample_metrics)
    print("\n===== 实验B 单轮评估结果 =====")
    for k, v in agg.items():
        print(f"  {k}: {v['mean']:.4f} (n={v['count']})")

    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    result = {"aggregate": agg, "num_samples": len(sample_metrics)}
    if args.save_details:
        result["details"] = details
    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果保存至 {args.output}")


if __name__ == "__main__":
    main()
