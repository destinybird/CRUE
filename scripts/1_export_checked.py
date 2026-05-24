#!/usr/bin/env python3
"""
export_checked.py — 收集 clean 样本对应的 sft_data 文件名，存入 clean_data.json

流程:
  1. 运行 validate_quality.py 生成最新报告
  2. 读取报告，收集所有 dirty sample_id
  3. 遍历 raw_results，对 clean 的 (nodule, patient) 找到对应 sft_data 文件名
  4. 保存文件名列表到 clean_data.json
"""

import json, subprocess, sys
from pathlib import Path

BASE = Path("/Users/yixuanli/Downloads/000_Workspaces/Lung_agent/code")
RAW_DIR = BASE / "output" / "raw_results"
SFT_DIR = BASE / "output" / "sft_data"
REPORT_PATH = BASE / "output" / "validation_report.json"
VALIDATE_SCRIPT = BASE / "scripts" / "validate_quality.py"
CLEAN_DATA_PATH = BASE / "output" / "clean_data.json"


def run_validate():
    """运行校验脚本生成最新报告"""
    print("[export] 运行 validate_quality.py ...")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[export] validate 失败:\n{result.stderr}")
        sys.exit(1)
    # 打印汇总行
    lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
    if lines:
        print(lines[-1])


def collect_dirty_ids(report: dict) -> set:
    """从报告中收集所有有 error 或 warning 的 sample_id"""
    dirty = set()
    for item in report.get("failed_details", []):
        dirty.add(item["sample_id"])
    for item in report.get("all_warnings", []):
        dirty.add(item["sample_id"])
    return dirty


def main():
    # Step 1: 运行校验
    run_validate()

    # Step 2: 读取报告
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    dirty_ids = collect_dirty_ids(report)
    total_samples = report["total_samples"]
    clean_count = report["clean"]
    print(f"[export] 总样本 {total_samples}, clean {clean_count}, dirty {len(dirty_ids)}")

    # Step 3: 遍历 raw 文件，收集 clean 样本对应的 sft_data 文件名
    clean_files = []
    missing = 0

    for fp in sorted(RAW_DIR.glob("*.json")):
        raw_data = json.loads(fp.read_text(encoding="utf-8"))
        nodule_id = raw_data.get("nodule_id", fp.stem)
        raw_stem = fp.stem  # e.g. "1_188_264.xml_5117"

        for dialog in raw_data.get("dialogs", []):
            patient_id = dialog.get("patient_id")
            sample_id = f"{nodule_id}_{patient_id}"

            if sample_id in dirty_ids:
                continue

            # Clean sample — 构建 sft 文件名
            sft_filename = f"{raw_stem}_{patient_id}.json"
            sft_path = SFT_DIR / sft_filename

            if sft_path.exists():
                clean_files.append(sft_filename)
            else:
                missing += 1

    # Step 4: 保存到 clean_data.json
    CLEAN_DATA_PATH.write_text(
        json.dumps(clean_files, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n{'='*50}")
    print(f"✅ 收集完成: {len(clean_files)} clean 文件名 → {CLEAN_DATA_PATH}")
    if missing:
        print(f"⚠️  {missing} 个 clean 样本在 sft_data 中未找到对应文件")
    if len(clean_files) != clean_count:
        print(f"⚠️  预期 {clean_count}, 实际 {len(clean_files)}")


if __name__ == "__main__":
    main()