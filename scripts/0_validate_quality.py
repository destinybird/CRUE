#!/usr/bin/env python3
"""
validate_quality.py — 肺结节数据质量校验 (v2)

统一从 raw_results/ 校验，不再单独存储SFT数据。
校验粒度: (nodule_id, patient_id)
模块:
  L1-Format       结构完整性
  L1-Cross        特征 vs CSV 交叉校验
  L1-ClinicalCtx  病历上下文内容校验
  L1-Dialog       对话结构与内容校验
  L1-EBM          规则覆盖校验
  L1-Consistency  内部一致性校验
"""

import json, sys, argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
import pandas as pd


# ============================================================
# 数据结构
# ============================================================

@dataclass
class Issue:
    level: str       # "ERROR" | "WARN"
    module: str
    field: str
    message: str

@dataclass
class SampleReport:
    sample_id: str   # "noduleId_patientId"
    source_file: str
    passed: bool = True
    issues: list = field(default_factory=list)
    error_count: int = 0
    warn_count: int = 0

    def add(self, issue: Issue):
        self.issues.append(asdict(issue))
        if issue.level == "ERROR":
            self.error_count += 1
            self.passed = False
        else:
            self.warn_count += 1


# ============================================================
# 数据加载
# ============================================================

FEAT_COLS = ["malignancy", "texture", "calcification", "margin",
             "sphericity", "lobulation", "spiculation", "diameter_mm"]

def _csv_key(patient_folder, xml_file, nodule_id) -> str:
    """构建唯一复合键: patient_folder + xml_file + nodule_id"""
    return f"{str(patient_folder).strip()}_{str(xml_file).strip()}_{str(nodule_id).strip()}"

def load_csv(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    idx = {}
    for _, r in df.iterrows():
        nid = str(r["nodule_id"]).strip() if pd.notna(r.get("nodule_id")) else ""
        pf = str(r.get("patient_folder", "")).strip()
        xf = str(r.get("xml_file", "")).strip()
        if nid:
            key = _csv_key(pf, xf, nid)
            idx[key] = r.to_dict()
    return idx

def load_ebm(ebm_path: Path) -> dict:
    df = pd.read_excel(ebm_path)
    rules = {}
    for _, r in df.iterrows():
        rid = str(r.get("Rule_ID", ""))
        if rid:
            rules[rid] = r.to_dict()
    return rules


# ============================================================
# L1-Format: 结构完整性 (per raw file)
# ============================================================

REQ_TOP = ["nodule_id", "nodule_features", "risk_assessment",
           "management_plan", "clinical_context", "dialogs"]
REQ_FEAT = FEAT_COLS
REQ_RISK = ["malignancy_score", "risk_level", "probability", "recommended_action"]
REQ_CTX = ["patient_id", "age", "gender", "smoking_history",
           "chief_complaint", "present_illness"]
REQ_DLG = ["patient_id", "turns", "num_turns"]


def validate_format(raw: dict, rpt: SampleReport):
    for k in REQ_TOP:
        if k not in raw:
            rpt.add(Issue("ERROR", "L1-Format", k, f"缺少顶层字段: {k}"))

    nf = raw.get("nodule_features", {})
    if isinstance(nf, dict):
        for k in REQ_FEAT:
            if k not in nf:
                rpt.add(Issue("ERROR", "L1-Format", f"nodule_features.{k}", f"缺少: {k}"))
    else:
        rpt.add(Issue("ERROR", "L1-Format", "nodule_features", "应为dict"))

    ra = raw.get("risk_assessment", {})
    if isinstance(ra, dict):
        for k in REQ_RISK:
            if k not in ra:
                rpt.add(Issue("ERROR", "L1-Format", f"risk_assessment.{k}", f"缺少: {k}"))
    else:
        rpt.add(Issue("ERROR", "L1-Format", "risk_assessment", "应为dict"))

    ctx_list = raw.get("clinical_context", [])
    if not isinstance(ctx_list, list) or len(ctx_list) == 0:
        rpt.add(Issue("ERROR", "L1-Format", "clinical_context", "应为非空list"))
    else:
        for i, ctx in enumerate(ctx_list):
            for k in REQ_CTX:
                if k not in ctx:
                    rpt.add(Issue("ERROR", "L1-Format", f"clinical_context[{i}].{k}", f"缺少: {k}"))

    dlg_list = raw.get("dialogs", [])
    if not isinstance(dlg_list, list) or len(dlg_list) == 0:
        rpt.add(Issue("ERROR", "L1-Format", "dialogs", "应为非空list"))
    else:
        for i, dlg in enumerate(dlg_list):
            for k in REQ_DLG:
                if k not in dlg:
                    rpt.add(Issue("ERROR", "L1-Format", f"dialogs[{i}].{k}", f"缺少: {k}"))
            turns = dlg.get("turns", [])
            if not isinstance(turns, list) or len(turns) == 0:
                rpt.add(Issue("ERROR", "L1-Format", f"dialogs[{i}].turns", "对话轮次为空"))
            else:
                for j, t in enumerate(turns):
                    if "role" not in t or "content" not in t:
                        rpt.add(Issue("ERROR", "L1-Format", f"dialogs[{i}].turns[{j}]", "缺role/content"))

    # patient_id 一致性
    ctx_pids = {c.get("patient_id") for c in ctx_list} if isinstance(ctx_list, list) else set()
    dlg_pids = {d.get("patient_id") for d in dlg_list} if isinstance(dlg_list, list) else set()
    if ctx_pids != dlg_pids:
        rpt.add(Issue("ERROR", "L1-Format", "patient_id_mismatch",
                       f"ctx pids {ctx_pids} != dlg pids {dlg_pids}"))


# ============================================================
# L1-Cross: 特征 vs CSV
# ============================================================

def validate_cross(raw: dict, csv_idx: dict, rpt: SampleReport):
    nid = str(raw.get("nodule_id", ""))
    nf = raw.get("nodule_features", {})
    pf = str(nf.get("patient_folder", "")).strip()
    xf = str(nf.get("xml_file", "")).strip()
    key = _csv_key(pf, xf, nid)
    if key not in csv_idx:
        rpt.add(Issue("ERROR", "L1-Cross", "nodule_id", f"{key} 不在CSV中"))
        return
    csv_row = csv_idx[key]

    for col in FEAT_COLS:
        rv, cv = nf.get(col), csv_row.get(col)
        if rv is None or cv is None:
            continue
        try:
            if abs(float(rv) - float(cv)) > 0.01:
                rpt.add(Issue("ERROR", "L1-Cross", col, f"raw={rv} vs csv={cv}"))
        except (ValueError, TypeError):
            pass

    # risk_level
    ra = raw.get("risk_assessment", {})
    rr = str(ra.get("risk_level", "")).strip().lower()
    cr = str(csv_row.get("risk_level", "")).strip().lower()
    if rr and cr and rr != cr:
        rpt.add(Issue("WARN", "L1-Cross", "risk_level", f"raw={rr} vs csv={cr}"))

    # 全零特征
    zeros = sum(1 for c in FEAT_COLS if float(nf.get(c, -1)) == 0)
    if zeros >= len(FEAT_COLS):
        rpt.add(Issue("WARN", "L1-Cross", "all_zero_features", "所有特征值为0，可能LIDC标注缺失"))


# ============================================================
# L1-ClinicalCtx: 病历上下文内容校验 (per patient)
# ============================================================

def validate_clinical_ctx(ctx: dict, nodule_id: str, rpt: SampleReport):
    pid = ctx.get("patient_id", "?")

    # 关键字段非空
    for k in ["age", "gender", "chief_complaint", "present_illness"]:
        v = ctx.get(k)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            rpt.add(Issue("ERROR", "L1-ClinicalCtx", f"{pid}.{k}", "字段为空"))

    # age 合理范围
    age = ctx.get("age")
    if age is not None:
        try:
            a = int(age)
            if a < 18 or a > 100:
                rpt.add(Issue("WARN", "L1-ClinicalCtx", f"{pid}.age", f"年龄={a}，超出常规范围"))
        except (ValueError, TypeError):
            rpt.add(Issue("WARN", "L1-ClinicalCtx", f"{pid}.age", f"年龄非数值: {age}"))

    # gender
    gender = str(ctx.get("gender", "")).strip()
    if gender and gender not in ("男", "女", "M", "F", "male", "female"):
        rpt.add(Issue("WARN", "L1-ClinicalCtx", f"{pid}.gender", f"性别异常: {gender}"))

    # present_illness 最小长度
    pi = str(ctx.get("present_illness", ""))
    if len(pi) < 10:
        rpt.add(Issue("WARN", "L1-ClinicalCtx", f"{pid}.present_illness", "现病史过短"))

    # full_text 存在性
    ft = ctx.get("full_text", "")
    if not ft or len(str(ft)) < 20:
        rpt.add(Issue("WARN", "L1-ClinicalCtx", f"{pid}.full_text", "完整病历文本过短或缺失"))


# ============================================================
# L1-Dialog: 对话结构与内容校验 (per patient)
# ============================================================

def validate_dialog(dlg: dict, nodule_id: str, nf: dict, ra: dict, mp: dict, rpt: SampleReport):
    pid = dlg.get("patient_id", "?")
    turns = dlg.get("turns", [])
    num = dlg.get("num_turns", 0)

    # 角色归一化: 兼容 patient/doctor 与 user/assistant 两套命名
    _ROLE_MAP = {"patient": "user", "doctor": "assistant"}
    for t in turns:
        t["role"] = _ROLE_MAP.get(t.get("role", ""), t.get("role", ""))

    # turns数量一致
    if len(turns) != num:
        rpt.add(Issue("WARN", "L1-Dialog", f"{pid}.num_turns", f"声明{num}轮 实际{len(turns)}轮"))

    if len(turns) == 0:
        rpt.add(Issue("ERROR", "L1-Dialog", f"{pid}.turns", "对话为空"))
        return

    # 角色交替: 应以user开头
    roles = [t.get("role", "") for t in turns]
    if roles[0] != "user":
        rpt.add(Issue("WARN", "L1-Dialog", f"{pid}.turns[0].role", f"首轮应为user，实际={roles[0]}"))

    # 检查空内容
    for i, t in enumerate(turns):
        c = str(t.get("content", "")).strip()
        if len(c) == 0:
            rpt.add(Issue("ERROR", "L1-Dialog", f"{pid}.turns[{i}].content", "内容为空"))

    # assistant回复应包含结节相关关键词
    kw_nodule = ["结节", "肺", "nodule", "CT", "影像", "磨玻璃", "实性"]
    has_nodule_ref = False
    for t in turns:
        if t.get("role") == "assistant":
            txt = str(t.get("content", ""))
            if any(k in txt for k in kw_nodule):
                has_nodule_ref = True
                break
    if not has_nodule_ref:
        rpt.add(Issue("WARN", "L1-Dialog", f"{pid}.content", "assistant回复未提及结节相关关键词"))

    # assistant回复应提及风险等级
    risk_level = str(ra.get("risk_level", ""))
    if risk_level:
        risk_mentioned = False
        risk_kws = [risk_level, risk_level.lower(), risk_level.upper()]
        # 中文映射
        risk_cn = {"low": "低", "medium": "中", "high": "高"}
        cn = risk_cn.get(risk_level.lower(), "")
        if cn:
            risk_kws.append(cn + "风险")
            risk_kws.append(cn + "危")
        for t in turns:
            if t.get("role") == "assistant":
                txt = str(t.get("content", ""))
                if any(k in txt for k in risk_kws):
                    risk_mentioned = True
                    break
        if not risk_mentioned:
            rpt.add(Issue("WARN", "L1-Dialog", f"{pid}.risk_mention",
                          f"assistant未提及风险等级 {risk_level}"))

    # 管理建议应在对话中有所体现
    mgmt_summary = str(mp.get("management_summary", ""))
    if mgmt_summary and len(mgmt_summary) > 5:
        action_kws = ["随访", "复查", "活检", "手术", "PET", "CT", "观察", "follow"]
        action_in_dialog = False
        for t in turns:
            if t.get("role") == "assistant":
                txt = str(t.get("content", ""))
                if any(k in txt for k in action_kws):
                    action_in_dialog = True
                    break
        if not action_in_dialog:
            rpt.add(Issue("WARN", "L1-Dialog", f"{pid}.action_mention",
                          "assistant未提及任何管理建议关键词"))


# ============================================================
# L1-EBM: 规则覆盖
# ============================================================

def validate_ebm(raw: dict, ebm_rules: dict, rpt: SampleReport):
    mp = raw.get("management_plan", {})
    # matched = mp.get("matched_rules_count", 0)
    # [FIX] 兼容pipeline输出的matched_rules(list)和旧格式matched_rules_count(int)
    _matched_rules = mp.get("matched_rules", [])
    matched = len(_matched_rules) if isinstance(_matched_rules, list) else mp.get("matched_rules_count", 0)
    if matched == 0:
        rpt.add(Issue("WARN", "L1-EBM", "matched_rules_count", "无匹配EBM规则"))

    # top_rules = mp.get("top_rules", [])
    # [FIX] 兼容pipeline输出的matched_rules(list)作为top_rules的fallback
    top_rules = mp.get("top_rules", _matched_rules)
    if isinstance(top_rules, list):
        for rule in top_rules:
            rid = str(rule.get("rule_id", "")) if isinstance(rule, dict) else ""
            if rid and rid not in ebm_rules:
                rpt.add(Issue("WARN", "L1-EBM", f"rule_{rid}", f"规则{rid}不在EBM表中"))

    summary = str(mp.get("management_summary", ""))
    if len(summary) < 10:
        rpt.add(Issue("WARN", "L1-EBM", "management_summary", "管理摘要过短"))


# ============================================================
# L1-Consistency: 内部一致性
# ============================================================

def validate_consistency(raw: dict, rpt: SampleReport):
    ra = raw.get("risk_assessment", {})
    nf = raw.get("nodule_features", {})

    # malignancy score vs risk_level
    try:
        ms = float(ra.get("malignancy_score", 0))
        rl = str(ra.get("risk_level", "")).lower()
        if ms <= 2 and rl == "high":
            rpt.add(Issue("WARN", "L1-Consistency", "score_vs_level",
                          f"malignancy_score={ms} 但 risk_level=high"))
        if ms >= 4 and rl == "low":
            rpt.add(Issue("WARN", "L1-Consistency", "score_vs_level",
                          f"malignancy_score={ms} 但 risk_level=low"))
    except (ValueError, TypeError):
        pass

    # malignancy in features vs risk_assessment
    feat_mal = nf.get("malignancy")
    risk_mal = ra.get("malignancy_score")
    if feat_mal is not None and risk_mal is not None:
        try:
            if abs(float(feat_mal) - float(risk_mal)) > 0.5:
                rpt.add(Issue("WARN", "L1-Consistency", "malignancy_mismatch",
                              f"features.malignancy={feat_mal} vs risk.score={risk_mal}"))
        except (ValueError, TypeError):
            pass


# ============================================================
# 主处理: 按 (nodule_id, patient_id) 粒度
# ============================================================

def process_file(fpath: Path, csv_idx: dict, ebm_rules: dict) -> list:
    """处理单个raw JSON，返回 SampleReport 列表 (每个patient一个)"""
    try:
        raw = json.loads(fpath.read_text(encoding="utf-8"))
    except Exception as e:
        r = SampleReport(fpath.stem, str(fpath))
        r.add(Issue("ERROR", "L1-Format", "json_parse", str(e)))
        return [r]

    nid = str(raw.get("nodule_id", fpath.stem))
    ctx_list = raw.get("clinical_context", [])
    dlg_list = raw.get("dialogs", [])
    nf = raw.get("nodule_features", {})
    ra = raw.get("risk_assessment", {})
    mp = raw.get("management_plan", {})

    # 建立 patient_id -> ctx/dlg 映射
    ctx_map = {c.get("patient_id"): c for c in ctx_list} if isinstance(ctx_list, list) else {}
    dlg_map = {d.get("patient_id"): d for d in dlg_list} if isinstance(dlg_list, list) else {}
    all_pids = sorted(set(list(ctx_map.keys()) + list(dlg_map.keys())))

    if not all_pids:
        # 无patient数据，仅做文件级校验
        r = SampleReport(f"{nid}_NO_PATIENT", str(fpath))
        validate_format(raw, r)
        validate_cross(raw, csv_idx, r)
        validate_ebm(raw, ebm_rules, r)
        validate_consistency(raw, r)
        return [r]

    reports = []

    # 文件级校验 (format/cross/ebm/consistency) 只做一次，挂到第一个patient
    file_rpt = SampleReport(f"{nid}_{all_pids[0]}", str(fpath))
    validate_format(raw, file_rpt)
    validate_cross(raw, csv_idx, file_rpt)
    validate_ebm(raw, ebm_rules, file_rpt)
    validate_consistency(raw, file_rpt)

    # 第一个patient还要做ctx+dialog校验
    if all_pids[0] in ctx_map:
        validate_clinical_ctx(ctx_map[all_pids[0]], nid, file_rpt)
    if all_pids[0] in dlg_map:
        validate_dialog(dlg_map[all_pids[0]], nid, nf, ra, mp, file_rpt)
    reports.append(file_rpt)

    # 其余patient只做ctx+dialog校验
    for pid in all_pids[1:]:
        r = SampleReport(f"{nid}_{pid}", str(fpath))
        if pid in ctx_map:
            validate_clinical_ctx(ctx_map[pid], nid, r)
        else:
            r.add(Issue("ERROR", "L1-ClinicalCtx", f"{pid}", "clinical_context中缺少该patient"))
        if pid in dlg_map:
            validate_dialog(dlg_map[pid], nid, nf, ra, mp, r)
        else:
            r.add(Issue("ERROR", "L1-Dialog", f"{pid}", "dialogs中缺少该patient"))
        reports.append(r)

    return reports


# ============================================================
# 汇总 & 输出
# ============================================================

def generate_summary(all_reports: list) -> dict:
    total = len(all_reports)
    passed = sum(1 for r in all_reports if r.passed)
    failed = total - passed
    total_errors = sum(r.error_count for r in all_reports)
    total_warns = sum(r.warn_count for r in all_reports)
    clean = sum(1 for r in all_reports if r.error_count == 0 and r.warn_count == 0)

    # 按模块统计 (预填所有模块，即使无issue也显示)
    ALL_MODULES = ["L1-Format", "L1-Cross", "L1-ClinicalCtx", "L1-Dialog", "L1-EBM", "L1-Consistency"]
    module_counts = {m: {"ERROR": 0, "WARN": 0} for m in ALL_MODULES}
    for r in all_reports:
        for iss in r.issues:
            mod = iss["module"]
            lv = iss["level"]
            module_counts.setdefault(mod, {"ERROR": 0, "WARN": 0})
            module_counts[mod][lv] += 1

    # 失败样本详情
    failed_details = []
    for r in all_reports:
        if not r.passed:
            failed_details.append({
                "sample_id": r.sample_id,
                "source_file": r.source_file,
                "error_count": r.error_count,
                "warn_count": r.warn_count,
                "issues": r.issues,
            })

    # 所有警告详情
    all_warnings = []
    for r in all_reports:
        for iss in r.issues:
            if iss["level"] == "WARN":
                all_warnings.append({
                    "sample_id": r.sample_id,
                    "module": iss["module"],
                    "field": iss["field"],
                    "msg": iss["message"],
                })

    return {
        "total_samples": total,
        "passed": passed,
        "failed": failed,
        "clean": clean,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "clean_rate": round(clean / total * 100, 1) if total else 0,
        "total_errors": total_errors,
        "total_warnings": total_warns,
        "by_module": module_counts,
        "failed_details": failed_details,
        "all_warnings": all_warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="肺结节数据质量校验 v2")
    parser.add_argument("--raw-dir", type=str,
                        default="/Users/yixuanli/Downloads/000_Workspaces/Lung_agent/code/output/raw_results")
    parser.add_argument("--csv", type=str,
                        default="/Users/yixuanli/Downloads/000_Workspaces/Lung_agent/code/data/processed/lidc_filtered_balanced.csv")
    parser.add_argument("--ebm", type=str,
                        default="/Users/yixuanli/Downloads/000_Workspaces/Lung_agent/code/data/rules/ebm.xlsx")
    parser.add_argument("--output", type=str,
                        default="/Users/yixuanli/Downloads/000_Workspaces/Lung_agent/code/output/validation_report.json")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    csv_path = Path(args.csv)
    ebm_path = Path(args.ebm)
    out_path = Path(args.output)

    print(f"[validate] raw_dir={raw_dir}")
    print(f"[validate] csv={csv_path}")
    print(f"[validate] ebm={ebm_path}")

    # 加载参考数据
    csv_idx = load_csv(csv_path)
    print(f"[validate] CSV loaded: {len(csv_idx)} nodules")

    ebm_rules = load_ebm(ebm_path) if ebm_path.exists() else {}
    print(f"[validate] EBM loaded: {len(ebm_rules)} rules")

    # 遍历raw文件
    raw_files = sorted(raw_dir.glob("*.json"))
    print(f"[validate] Found {len(raw_files)} raw files")

    all_reports = []
    for fp in raw_files:
        reports = process_file(fp, csv_idx, ebm_rules)
        all_reports.extend(reports)

    # 汇总
    summary = generate_summary(all_reports)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"校验完成: {summary['total_samples']} 样本, "
          f"通过 {summary['passed']}, 失败 {summary['failed']}, "
          f"通过率 {summary['pass_rate']}%")
    print(f"错误 {summary['total_errors']}, 警告 {summary['total_warnings']}")
    print(f"\n✅ 完全干净(0 error + 0 warning): {summary['clean']} 样本, "
          f"占比 {summary['clean_rate']}%")
    for mod, cnt in summary["by_module"].items():
        print(f"  {mod}: {cnt['ERROR']}E / {cnt['WARN']}W")
    print(f"报告已保存: {out_path}")


if __name__ == "__main__":
    main()
