#!/usr/bin/env python3
"""
eval_multi_turn.py - 实验B多轮评估

指标:
  1. ROUGE-L           (逐turn计算，每turn有自己的expected_response)
  2. Rule Recall       (session级累积：拼接全部turn输出后整体评估)
  3. Rule Precision    (session级：模型遵循的规则中属于GT的比例)
  4. Rule F1           (Recall与Precision的调和平均)
  5. Information Gain  (逐turn计算：每轮相对历史轮次的新信息比例)

用法:
    python eval_multi_turn.py \
        --predictions ../../data/outputs/expB_multi_turn.jsonl \
        --ground_truth ../../data/ground_truth/multi_turn_gt.jsonl \
        --ebm_rules ../../data/rules/ebm.xlsx \
        --output ../../data/results/expB_multi_turn_metrics.json
"""
import argparse
import json
import os
import re
from collections import defaultdict
from tqdm import tqdm
from eval_utils_rules import (
    load_ebm_rules, evaluate_single_sample, aggregate_metrics,
    compute_rouge_l, compute_rule_recall, compute_rule_precision,
)


def _tokenize(text: str) -> list:
    """中文按字切分，英文按词切分"""
    tokens = []
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            tokens.append(ch)
        elif ch.isalnum():
            if tokens and tokens[-1].isalnum():
                tokens[-1] += ch
            else:
                tokens.append(ch)
    return tokens


def compute_info_gain(current_text: str, history_texts: list, n: int = 2) -> float:
    """计算当前turn相对历史所有turn的信息增量（novel n-gram ratio）
    
    info_gain = |ngrams(current) - ngrams(history)| / |ngrams(current)|
    值越高 → 新信息越多；值越低 → 重复内容越多
    """
    if not current_text.strip():
        return 0.0

    cur_tokens = _tokenize(current_text.lower())
    if len(cur_tokens) < n:
        return 1.0

    cur_ngrams = set(tuple(cur_tokens[i:i+n]) for i in range(len(cur_tokens) - n + 1))
    if not cur_ngrams:
        return 1.0

    # 构建历史n-gram集合
    hist_ngrams = set()
    for ht in history_texts:
        ht_tokens = _tokenize(ht.lower())
        for i in range(len(ht_tokens) - n + 1):
            hist_ngrams.add(tuple(ht_tokens[i:i+n]))

    novel = cur_ngrams - hist_ngrams
    return len(novel) / len(cur_ngrams)


def main():
    parser = argparse.ArgumentParser()
    base = os.path.join(os.path.dirname(__file__), "..", "..")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--ground_truth", default=os.path.join(base, "data/ground_truth/multi_turn_gt.jsonl"))
    parser.add_argument("--single_gt", default=os.path.join(base, "data/ground_truth/single_turn_gt.jsonl"),
                        help="单轮GT，用于获取matched_rules_text")
    parser.add_argument("--ebm_rules", default=os.path.join(base, "data/rules/ebm.xlsx"))
    parser.add_argument("--output", default=os.path.join(base, "data/results/expB_multi_turn_metrics.json"))
    parser.add_argument("--save_details", action="store_true")
    args = parser.parse_args()

    ebm_rules = load_ebm_rules(args.ebm_rules)
    print(f"EBM规则: {len(ebm_rules)} 条")

    # 加载单轮GT的规则映射 (sample_id -> matched_rules_text)
    single_gt_rules = {}
    with open(args.single_gt) as f:
        for line in f:
            item = json.loads(line)
            single_gt_rules[item["id"]] = item.get("matched_rules_text", "")

    # 加载预测和GT
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

    matched_ids = set(preds.keys()) & set(gts.keys())
    print(f"匹配turn: {len(matched_ids)}/{len(preds)}")

    # ── 按session分组 ──
    sessions = defaultdict(list)  # sample_id -> [(turn_index, pred_item, gt_item)]
    for tid in matched_ids:
        pred_item = preds[tid]
        gt_item = gts[tid]
        sid = pred_item.get("sample_id", "")
        ti = pred_item.get("turn_index", 0)
        sessions[sid].append((ti, pred_item, gt_item))

    # 每个session内按turn_index排序
    for sid in sessions:
        sessions[sid].sort(key=lambda x: x[0])

    # ── 逐session评估 ──
    all_turn_metrics = []       # 逐turn: rouge_l + info_gain
    session_rule_metrics = []   # 逐session: rule_recall
    turn_groups = defaultdict(list)

    for sid in tqdm(sorted(sessions.keys()), desc="评估中"):
        turns = sessions[sid]
        rules_text = single_gt_rules.get(sid, "")

        # --- 1. Session级规则评估：拼接所有turn的prediction ---
        all_preds_concat = "\n".join(t[1]["prediction"] for t in turns)
        recall_result = compute_rule_recall(all_preds_concat, rules_text, ebm_rules)
        precision_result = compute_rule_precision(all_preds_concat, rules_text, ebm_rules)

        r = recall_result["rule_recall"]
        p = precision_result["rule_precision"]
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        session_rule = {
            "sample_id": sid,
            "rule_recall": r,
            "rule_precision": p,
            "rule_f1": f1,
            "rule_recall_detail": recall_result,
            "rule_precision_detail": precision_result,
        }
        session_rule_metrics.append(session_rule)

        # --- 2. 逐turn: ROUGE-L + Information Gain ---
        history_preds = []
        for ti, pred_item, gt_item in turns:
            pred_text = pred_item["prediction"]
            ref_text = gt_item.get("expected_response", "")

            rouge_l = compute_rouge_l(pred_text, ref_text)
            info_gain = compute_info_gain(pred_text, history_preds) if history_preds else 1.0

            turn_metric = {
                "id": pred_item["id"],
                "sample_id": sid,
                "turn_index": ti,
                "rouge_l": rouge_l,
                "info_gain": info_gain,
            }
            all_turn_metrics.append(turn_metric)
            turn_groups[ti].append(turn_metric)
            history_preds.append(pred_text)

    # ══════ 汇总输出 ══════

    # 全局 ROUGE-L + Info Gain（逐turn均值）
    avg_rouge = sum(m["rouge_l"] for m in all_turn_metrics) / len(all_turn_metrics) if all_turn_metrics else 0
    avg_info_gain = sum(m["info_gain"] for m in all_turn_metrics) / len(all_turn_metrics) if all_turn_metrics else 0
    # 排除turn0的info_gain（turn0恒为1.0，不反映增量能力）
    non_first = [m["info_gain"] for m in all_turn_metrics if m["turn_index"] > 0]
    avg_info_gain_nonfirst = sum(non_first) / len(non_first) if non_first else 0

    # 全局 Rule Recall / Precision / F1（session级均值）
    avg_recall = sum(m["rule_recall"] for m in session_rule_metrics) / len(session_rule_metrics) if session_rule_metrics else 0
    avg_precision = sum(m["rule_precision"] for m in session_rule_metrics) / len(session_rule_metrics) if session_rule_metrics else 0
    avg_f1 = sum(m["rule_f1"] for m in session_rule_metrics) / len(session_rule_metrics) if session_rule_metrics else 0

    print("\n===== 实验B 多轮评估结果（全局） =====")
    print(f"  rouge_l (per-turn):           {avg_rouge:.4f}  (n={len(all_turn_metrics)} turns)")
    print(f"  rule_recall (per-session):    {avg_recall:.4f}  (n={len(session_rule_metrics)} sessions)")
    print(f"  rule_precision (per-session): {avg_precision:.4f}  (n={len(session_rule_metrics)} sessions)")
    print(f"  rule_f1 (per-session):        {avg_f1:.4f}  (n={len(session_rule_metrics)} sessions)")
    print(f"  info_gain (per-turn):         {avg_info_gain:.4f}  (all turns)")
    print(f"  info_gain (turn>0 only):      {avg_info_gain_nonfirst:.4f}  (n={len(non_first)} turns)")

    # 按turn_index汇总
    print("\n===== 按轮次分布 =====")
    for ti in sorted(turn_groups.keys()):
        tg = turn_groups[ti]
        r = sum(m["rouge_l"] for m in tg) / len(tg)
        ig = sum(m["info_gain"] for m in tg) / len(tg)
        print(f"  turn {ti}: rouge_l={r:.4f}  info_gain={ig:.4f}  (n={len(tg)})")

    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    result = {
        "aggregate_global": {
            "rouge_l": {"mean": avg_rouge, "count": len(all_turn_metrics), "level": "per-turn"},
            "rule_recall": {"mean": avg_recall, "count": len(session_rule_metrics), "level": "per-session"},
            "rule_precision": {"mean": avg_precision, "count": len(session_rule_metrics), "level": "per-session"},
            "rule_f1": {"mean": avg_f1, "count": len(session_rule_metrics), "level": "per-session"},
            "info_gain": {"mean": avg_info_gain_nonfirst, "count": len(non_first), "level": "per-turn (turn>0)"},
        },
        "per_turn_index": {
            str(ti): {
                "rouge_l": sum(m["rouge_l"] for m in tg) / len(tg),
                "info_gain": sum(m["info_gain"] for m in tg) / len(tg),
                "count": len(tg),
            }
            for ti, tg in sorted(turn_groups.items())
        },
        "num_turns": len(all_turn_metrics),
        "num_sessions": len(session_rule_metrics),
    }
    if args.save_details:
        result["turn_details"] = all_turn_metrics
        result["session_rule_details"] = session_rule_metrics
    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果保存至 {args.output}")


if __name__ == "__main__":
    main()