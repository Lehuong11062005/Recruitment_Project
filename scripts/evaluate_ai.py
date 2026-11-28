"""Pipeline kiểm định Dataset CV_JD, đánh giá trích xuất kỹ năng và so sánh cấu hình trọng số AI Matching.

Sử dụng trực tiếp AI Service thực tế (mặc định http://127.0.0.1:8002) mà không sao chép thuật toán AI,
không chỉnh sửa gói dữ liệu gốc (đọc trực tiếp từ file ZIP hoặc thư mục giải nén) và tuyệt đối
không tự sinh nhãn Ground Truth giả.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import logging
import math
import re
import time
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import fitz
import httpx

DEFAULT_AI_URL = "http://127.0.0.1:8002"
DEFAULT_ZIP_PATH = Path("CV/CV_JD-20261127T160544Z-1-001.zip")
DEFAULT_OUT_DIR = Path("docs/ai_matching/evaluation_results")

WEIGHT_CONFIGS: Dict[str, Dict[str, float]] = {
    "baseline_50_35_15": {
        "skill_weight": 0.50,
        "semantic_weight": 0.35,
        "experience_weight": 0.15,
    },
    "config_a_60_25_15": {
        "skill_weight": 0.60,
        "semantic_weight": 0.25,
        "experience_weight": 0.15,
    },
    "config_b_40_20_40": {
        "skill_weight": 0.40,
        "semantic_weight": 0.20,
        "experience_weight": 0.40,
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("evaluate_ai")


def normalize_skill_key(name: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", name or "").casefold().strip())


def parse_semicolon_skills(raw: str) -> List[str]:
    if not raw or not raw.strip():
        return []
    return [item.strip() for item in raw.split(";") if item.strip()]


def parse_years_from_text(raw: Any) -> float:
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text:
        return 0.0
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if not match:
        return 0.0
    return float(match.group(1).replace(",", "."))


class DatasetArchive:
    """Đọc dữ liệu chuẩn CV_JD từ file ZIP hoặc thư mục mà không làm thay đổi dữ liệu gốc."""

    def __init__(self, source: Path):
        self.source = source
        self.is_zip = source.is_file() and source.suffix.lower() == ".zip"
        self._zip: Optional[zipfile.ZipFile] = zipfile.ZipFile(source, "r") if self.is_zip else None
        self._prefix = "CV_JD/" if self.is_zip else ""

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def list_files(self, subdir: str, suffix: str) -> List[str]:
        if self._zip is not None:
            prefix = f"{self._prefix}{subdir}/"
            return sorted(
                Path(name).name
                for name in self._zip.namelist()
                if name.startswith(prefix) and name.lower().endswith(suffix.lower())
            )
        folder = self.source / subdir
        return sorted(p.name for p in folder.glob(f"*{suffix}"))

    def read_bytes(self, rel_path: str) -> bytes:
        if self._zip is not None:
            return self._zip.read(f"{self._prefix}{rel_path}")
        return (self.source / rel_path).read_bytes()

    def read_text(self, rel_path: str) -> str:
        return self.read_bytes(rel_path).decode("utf-8-sig")


def build_taxonomy_lookup(taxonomy: List[Dict[str, Any]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for entry in taxonomy:
        canonical = (entry.get("skill") or "").strip()
        if not canonical:
            continue
        lookup[normalize_skill_key(canonical)] = canonical
        for alias in entry.get("aliases") or []:
            if isinstance(alias, str) and alias.strip():
                lookup.setdefault(normalize_skill_key(alias), canonical)
    return lookup


def canonicalize_skills(skills: Iterable[str], lookup: Dict[str, str]) -> Tuple[Set[str], List[str]]:
    canonical_set: Set[str] = set()
    unmapped: List[str] = []
    for raw in skills:
        key = normalize_skill_key(raw)
        if not key:
            continue
        mapped = lookup.get(key)
        if mapped:
            canonical_set.add(mapped)
        else:
            unmapped.append(raw.strip())
    return canonical_set, unmapped


def audit_dataset(
    archive: DatasetArchive,
    ai_taxonomy: List[Dict[str, Any]],
    pair_gt_path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    cv_pdf_files = archive.list_files("cv", ".pdf")
    jd_txt_files = archive.list_files("jd", ".txt")
    cv_rows = list(csv.DictReader(io.StringIO(archive.read_text("cv_metadata.csv"))))
    jd_rows = list(csv.DictReader(io.StringIO(archive.read_text("jd_metadata.csv"))))
    dataset_tax = json.loads(archive.read_text("skill_taxonomy.json"))
    readme_text = archive.read_text("README.md")

    lookup = build_taxonomy_lookup(ai_taxonomy)

    cv_meta_names = [r["file"].strip() for r in cv_rows]
    jd_meta_names = [r["file"].strip() for r in jd_rows]

    unreadable_pdfs: List[Dict[str, str]] = []
    pdf_hashes: Dict[str, List[str]] = {}
    empty_skill_gt_cvs: List[str] = []
    unmapped_gt_skills: Dict[str, List[str]] = {}
    n_skills_mismatches: List[Dict[str, Any]] = []

    for row in cv_rows:
        fn = row["file"].strip()
        pdf_bytes = archive.read_bytes(f"cv/{fn}")
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        pdf_hashes.setdefault(digest, []).append(fn)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            txt = "\n".join(page.get_text("text") for page in doc).strip()
            doc.close()
            if not txt:
                unreadable_pdfs.append({"file": fn, "reason": "empty_extracted_text"})
        except Exception as exc:
            unreadable_pdfs.append({"file": fn, "reason": str(exc)})

        gt_list = parse_semicolon_skills(row.get("skills_ground_truth", ""))
        if not gt_list:
            empty_skill_gt_cvs.append(fn)
        _, unmapped = canonicalize_skills(gt_list, lookup)
        if unmapped:
            unmapped_gt_skills[fn] = unmapped
        declared_n = int(row.get("n_skills") or 0)
        if declared_n != len(gt_list):
            n_skills_mismatches.append({"file": fn, "declared": declared_n, "actual": len(gt_list)})

    jd_unmapped: Dict[str, List[str]] = {}
    for row in jd_rows:
        fn = row["file"].strip()
        req = parse_semicolon_skills(row.get("required_skills", ""))
        _, unmapped = canonicalize_skills(req, lookup)
        if unmapped:
            jd_unmapped[fn] = unmapped

    duplicate_pdfs = {h: files for h, files in pdf_hashes.items() if len(files) > 1}

    has_pair_score_gt = False
    has_pair_relevance_gt = False
    pair_gt_count = 0
    if pair_gt_path and pair_gt_path.is_file():
        gt_rows = list(csv.DictReader(io.StringIO(pair_gt_path.read_text(encoding="utf-8-sig"))))
        pair_gt_count = len(gt_rows)
        if gt_rows:
            cols = set(gt_rows[0].keys())
            has_pair_score_gt = bool(cols & {"human_score", "ground_truth_score"})
            has_pair_relevance_gt = bool(cols & {"relevant", "is_relevant", "relevance"})

    audit_summary = {
        "dataset_source": str(archive.source),
        "cv_pdf_count": len(cv_pdf_files),
        "jd_txt_count": len(jd_txt_files),
        "cv_metadata_rows": len(cv_rows),
        "jd_metadata_rows": len(jd_rows),
        "total_cv_jd_pairs": len(cv_rows) * len(jd_rows),
        "cv_filename_exact_match": sorted(cv_pdf_files) == sorted(cv_meta_names),
        "jd_filename_exact_match": sorted(jd_txt_files) == sorted(jd_meta_names),
        "unreadable_or_empty_pdfs": unreadable_pdfs,
        "duplicate_pdfs_by_sha256": duplicate_pdfs,
        "cvs_with_empty_skills_ground_truth": empty_skill_gt_cvs,
        "unmapped_cv_ground_truth_skills": unmapped_gt_skills,
        "unmapped_jd_required_skills": jd_unmapped,
        "n_skills_column_mismatches": n_skills_mismatches,
        "dataset_taxonomy_count": len(dataset_tax),
        "ai_service_taxonomy_count": len(ai_taxonomy),
        "ground_truth_labeling_note": (
            "Theo README.md của bộ dữ liệu, skills_ground_truth chỉ được gán nhãn từ mục 'Kỹ năng' "
            "của CV (không bao gồm kỹ năng chỉ nhắc tới trong phần Kinh nghiệm/Dự án)."
        ),
        "human_pair_score_ground_truth_available": has_pair_score_gt,
        "human_pair_relevance_ground_truth_available": has_pair_relevance_gt,
        "human_pair_ground_truth_rows": pair_gt_count,
        "mae_status": "READY" if has_pair_score_gt else "BLOCKED (Missing Human Ground Truth CV-JD scores)",
        "precision_at_5_status": (
            "READY" if has_pair_relevance_gt else "BLOCKED (Missing Human Ground Truth CV-JD relevance labels)"
        ),
        "readme_excerpt": readme_text.strip(),
    }
    return audit_summary, cv_rows, jd_rows


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retries: int = 2,
    **kwargs: Any,
) -> httpx.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def evaluate_skill_extraction(
    cv_rows: List[Dict[str, Any]],
    parsed_cvs: Dict[str, Dict[str, Any]],
    lookup: Dict[str, str],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    per_cv_metrics: List[Dict[str, Any]] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    macro_p_all: List[float] = []
    macro_r_all: List[float] = []
    macro_f1_all: List[float] = []

    macro_p_nonempty: List[float] = []
    macro_r_nonempty: List[float] = []
    macro_f1_nonempty: List[float] = []

    for row in cv_rows:
        fn = row["file"].strip()
        gt_raw = parse_semicolon_skills(row.get("skills_ground_truth", ""))
        gt_set, _ = canonicalize_skills(gt_raw, lookup)

        parsed = parsed_cvs[fn]
        pred_raw = parsed.get("skills") or []
        pred_set, _ = canonicalize_skills(pred_raw, lookup)

        tp_skills = sorted(gt_set & pred_set)
        fp_skills = sorted(pred_set - gt_set)
        fn_skills = sorted(gt_set - pred_set)

        tp = len(tp_skills)
        fp = len(fp_skills)
        fn_cnt = len(fn_skills)

        total_tp += tp
        total_fp += fp
        total_fn += fn_cnt

        if len(gt_set) == 0 and len(pred_set) == 0:
            precision = 1.0
            recall = 1.0
            f1 = 1.0
        else:
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn_cnt) if (tp + fn_cnt) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        macro_p_all.append(precision)
        macro_r_all.append(recall)
        macro_f1_all.append(f1)

        if len(gt_set) > 0:
            macro_p_nonempty.append(precision)
            macro_r_nonempty.append(recall)
            macro_f1_nonempty.append(f1)

        per_cv_metrics.append(
            {
                "file": fn,
                "candidate_name": row.get("candidate_name", ""),
                "industry": row.get("industry", ""),
                "role": row.get("role", ""),
                "level": row.get("level", ""),
                "layout": row.get("layout", ""),
                "gt_count": len(gt_set),
                "pred_count": len(pred_set),
                "tp": tp,
                "fp": fp,
                "fn": fn_cnt,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "gt_skills": "; ".join(sorted(gt_set)),
                "pred_skills": "; ".join(sorted(pred_set)),
                "fp_skills": "; ".join(fp_skills),
                "fn_skills": "; ".join(fn_skills),
            }
        )

    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) > 0 else 0.0

    summary = {
        "evaluated_cvs_total": len(cv_rows),
        "cvs_with_nonempty_gt": len(macro_p_nonempty),
        "cvs_with_empty_gt": len(cv_rows) - len(macro_p_nonempty),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_all_46_precision": round(sum(macro_p_all) / len(macro_p_all), 4),
        "macro_all_46_recall": round(sum(macro_r_all) / len(macro_r_all), 4),
        "macro_all_46_f1": round(sum(macro_f1_all) / len(macro_f1_all), 4),
        "macro_nonempty_44_precision": round(sum(macro_p_nonempty) / len(macro_p_nonempty), 4),
        "macro_nonempty_44_recall": round(sum(macro_r_nonempty) / len(macro_r_nonempty), 4),
        "macro_nonempty_44_f1": round(sum(macro_f1_nonempty) / len(macro_f1_nonempty), 4),
    }
    return summary, per_cv_metrics


def spearman_rank_corr(ranks_a: List[int], ranks_b: List[int]) -> float:
    n = len(ranks_a)
    if n <= 1:
        return 1.0
    d2 = sum((a - b) ** 2 for a, b in zip(ranks_a, ranks_b))
    return round(1.0 - (6.0 * d2) / (n * (n * n - 1)), 4)


async def run_pipeline(
    ai_url: str,
    dataset_source: Path,
    out_dir: Path,
    pair_gt_path: Optional[Path] = None,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = out_dir / "checkpoint_parse_and_match.json"
    checkpoint: Dict[str, Any] = {"parsed_cvs": {}, "pair_matches": {}}
    if checkpoint_file.exists():
        checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))

    ai_tax_path = Path("services/ai-service/app/core/skill_taxonomy.json")
    ai_taxonomy = json.loads(ai_tax_path.read_text(encoding="utf-8"))
    lookup = build_taxonomy_lookup(ai_taxonomy)

    archive = DatasetArchive(dataset_source)
    try:
        audit_info, cv_rows, jd_rows = audit_dataset(archive, ai_taxonomy, pair_gt_path)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Check live AI Service health
            health_resp = await request_with_retry(client, "GET", f"{ai_url.rstrip('/')}/health")
            health_info = health_resp.json()
            logger.info("Connected to AI Service: %s", health_info)

            # 2. Parse all 46 CVs via POST /api/v1/ai/parse-cv
            parsed_cvs: Dict[str, Dict[str, Any]] = checkpoint.setdefault("parsed_cvs", {})
            for idx, cv_row in enumerate(cv_rows, 1):
                fn = cv_row["file"].strip()
                if fn not in parsed_cvs:
                    pdf_bytes = archive.read_bytes(f"cv/{fn}")
                    resp = await request_with_retry(
                        client,
                        "POST",
                        f"{ai_url.rstrip('/')}/api/v1/ai/parse-cv",
                        files={"file": (fn, pdf_bytes, "application/pdf")},
                    )
                    payload = resp.json()
                    parsed_cvs[fn] = {
                        "parsed_text": payload["parsed_text"],
                        "skills": payload["skills"],
                    }
                    checkpoint_file.write_text(
                        json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                logger.info("[%02d/%02d] Parsed %s -> %d skills", idx, len(cv_rows), fn, len(parsed_cvs[fn]["skills"]))

            skill_summary, skill_rows = evaluate_skill_extraction(cv_rows, parsed_cvs, lookup)

            # 3. Evaluate 644 CV-JD pairs via POST /api/v1/ai/match across 3 weight configs
            jd_texts = {
                r["file"].strip(): archive.read_text(f"jd/{r['file'].strip()}")
                for r in jd_rows
            }
            pair_matches: Dict[str, Dict[str, Any]] = checkpoint.setdefault("pair_matches", {})

            # Note: Since component scores (skill_score, semantic_score, experience_score) are identical across
            # weight configs, we still invoke POST /api/v1/ai/match with each config's matching_weights so the
            # real AI Service validates weights, computes ai_match_score, and returns matching_weights_snapshot!
            sem = asyncio.Semaphore(6)

            async def _eval_one_pair(cfg_name: str, weights: Dict[str, float], cv_r: Dict[str, Any], jd_r: Dict[str, Any]) -> None:
                cv_fn = cv_r["file"].strip()
                jd_fn = jd_r["file"].strip()
                key = f"{cfg_name}::{jd_fn}::{cv_fn}"
                if key in pair_matches:
                    return
                parsed_cv = parsed_cvs[cv_fn]
                req_skills = parse_semicolon_skills(jd_r.get("required_skills", ""))
                cand_years = parse_years_from_text(cv_r.get("years_experience", 0))
                job_years = parse_years_from_text(jd_r.get("experience_required", 0))
                body = {
                    "cv_text": parsed_cv["parsed_text"],
                    "jd_text": f"{jd_r.get('position', '')}\n{jd_texts[jd_fn]}",
                    "candidate_skills": parsed_cv["skills"],
                    "required_skills": req_skills,
                    "candidate_experience_years": cand_years,
                    "job_experience_required": job_years,
                    "matching_weights": weights,
                }
                async with sem:
                    resp = await request_with_retry(
                        client,
                        "POST",
                        f"{ai_url.rstrip('/')}/api/v1/ai/match",
                        json=body,
                    )
                    res = resp.json()
                pair_matches[key] = {
                    "config": cfg_name,
                    "jd_file": jd_fn,
                    "jd_position": jd_r.get("position", ""),
                    "cv_file": cv_fn,
                    "candidate_name": cv_r.get("candidate_name", ""),
                    "cv_industry": cv_r.get("industry", ""),
                    "cv_role": cv_r.get("role", ""),
                    "cand_years": cand_years,
                    "job_years": job_years,
                    "ai_match_score": res["ai_match_score"],
                    "matching_version": res["matching_version"],
                    "skill_score": res["score_breakdown"]["skill_score"],
                    "semantic_score": res["score_breakdown"]["semantic_score"],
                    "experience_score": res["score_breakdown"]["experience_score"],
                    "weights_snapshot": res["matching_weights_snapshot"],
                    "matched_count": len(res["ai_analysis"]["matched"]),
                    "missing_count": len(res["ai_analysis"]["missing"]),
                }

            started = time.perf_counter()
            for cfg_name, weights in WEIGHT_CONFIGS.items():
                logger.info("Evaluating 644 CV-JD pairs for %s (%s)...", cfg_name, weights)
                tasks = [
                    _eval_one_pair(cfg_name, weights, cv_r, jd_r)
                    for jd_r in jd_rows
                    for cv_r in cv_rows
                ]
                await asyncio.gather(*tasks)
                checkpoint_file.write_text(
                    json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8"
                )
            elapsed = round(time.perf_counter() - started, 2)
            logger.info("Completed 3 x 644 = 1,932 AI Service matching evaluations in %.2fs", elapsed)

        # 4. Aggregate score & rank shift comparisons across 3 weight configs
        comparison_rows: List[Dict[str, Any]] = []
        per_jd_rank_shifts: List[Dict[str, Any]] = []
        config_stats: Dict[str, Dict[str, Any]] = {}

        for cfg_name in WEIGHT_CONFIGS:
            scores = [
                pair_matches[f"{cfg_name}::{jd_r['file'].strip()}::{cv_r['file'].strip()}"]["ai_match_score"]
                for jd_r in jd_rows
                for cv_r in cv_rows
            ]
            mean_s = sum(scores) / len(scores)
            std_s = math.sqrt(sum((x - mean_s) ** 2 for x in scores) / len(scores))
            config_stats[cfg_name] = {
                "weights": WEIGHT_CONFIGS[cfg_name],
                "pairs_evaluated": len(scores),
                "mean_score": round(mean_s, 2),
                "std_score": round(std_s, 2),
                "min_score": round(min(scores), 1),
                "max_score": round(max(scores), 1),
                "ge_80_count": sum(1 for s in scores if s >= 80.0),
                "between_60_80_count": sum(1 for s in scores if 60.0 <= s < 80.0),
                "lt_60_count": sum(1 for s in scores if s < 60.0),
            }

        for jd_r in jd_rows:
            jd_fn = jd_r["file"].strip()
            ranked_by_cfg: Dict[str, List[Dict[str, Any]]] = {}
            rank_pos: Dict[str, Dict[str, int]] = {}
            for cfg_name in WEIGHT_CONFIGS:
                items = [
                    pair_matches[f"{cfg_name}::{jd_fn}::{cv_r['file'].strip()}"]
                    for cv_r in cv_rows
                ]
                items_sorted = sorted(
                    items, key=lambda x: (-x["ai_match_score"], x["cv_file"])
                )
                ranked_by_cfg[cfg_name] = items_sorted
                rank_pos[cfg_name] = {
                    item["cv_file"]: rank_idx
                    for rank_idx, item in enumerate(items_sorted, 1)
                }

            base_top5 = [x["cv_file"] for x in ranked_by_cfg["baseline_50_35_15"][:5]]
            cfga_top5 = [x["cv_file"] for x in ranked_by_cfg["config_a_60_25_15"][:5]]
            cfgb_top5 = [x["cv_file"] for x in ranked_by_cfg["config_b_40_20_40"][:5]]

            cv_order = [cv_r["file"].strip() for cv_r in cv_rows]
            base_ranks = [rank_pos["baseline_50_35_15"][c] for c in cv_order]
            cfga_ranks = [rank_pos["config_a_60_25_15"][c] for c in cv_order]
            cfgb_ranks = [rank_pos["config_b_40_20_40"][c] for c in cv_order]

            per_jd_rank_shifts.append(
                {
                    "jd_file": jd_fn,
                    "jd_position": jd_r.get("position", ""),
                    "experience_required": jd_r.get("experience_required", ""),
                    "top1_baseline": base_top5[0],
                    "top1_config_a": cfga_top5[0],
                    "top1_config_b": cfgb_top5[0],
                    "top5_overlap_base_vs_a": len(set(base_top5) & set(cfga_top5)),
                    "top5_overlap_base_vs_b": len(set(base_top5) & set(cfgb_top5)),
                    "spearman_base_vs_a": spearman_rank_corr(base_ranks, cfga_ranks),
                    "spearman_base_vs_b": spearman_rank_corr(base_ranks, cfgb_ranks),
                    "max_rank_change_vs_a": max(abs(a - b) for a, b in zip(base_ranks, cfga_ranks)),
                    "max_rank_change_vs_b": max(abs(a - b) for a, b in zip(base_ranks, cfgb_ranks)),
                    "top5_baseline_list": "; ".join(base_top5),
                    "top5_config_a_list": "; ".join(cfga_top5),
                    "top5_config_b_list": "; ".join(cfgb_top5),
                }
            )

            for cv_r in cv_rows:
                cv_fn = cv_r["file"].strip()
                b = pair_matches[f"baseline_50_35_15::{jd_fn}::{cv_fn}"]
                ca = pair_matches[f"config_a_60_25_15::{jd_fn}::{cv_fn}"]
                cb = pair_matches[f"config_b_40_20_40::{jd_fn}::{cv_fn}"]
                comparison_rows.append(
                    {
                        "jd_file": jd_fn,
                        "jd_position": b["jd_position"],
                        "cv_file": cv_fn,
                        "candidate_name": b["candidate_name"],
                        "cv_industry": b["cv_industry"],
                        "cv_role": b["cv_role"],
                        "cand_years": b["cand_years"],
                        "job_years": b["job_years"],
                        "skill_score": b["skill_score"],
                        "semantic_score": b["semantic_score"],
                        "experience_score": b["experience_score"],
                        "score_baseline_50_35_15": b["ai_match_score"],
                        "rank_baseline": rank_pos["baseline_50_35_15"][cv_fn],
                        "score_config_a_60_25_15": ca["ai_match_score"],
                        "rank_config_a": rank_pos["config_a_60_25_15"][cv_fn],
                        "delta_score_a": round(ca["ai_match_score"] - b["ai_match_score"], 1),
                        "delta_rank_a": rank_pos["baseline_50_35_15"][cv_fn] - rank_pos["config_a_60_25_15"][cv_fn],
                        "score_config_b_40_20_40": cb["ai_match_score"],
                        "rank_config_b": rank_pos["config_b_40_20_40"][cv_fn],
                        "delta_score_b": round(cb["ai_match_score"] - b["ai_match_score"], 1),
                        "delta_rank_b": rank_pos["baseline_50_35_15"][cv_fn] - rank_pos["config_b_40_20_40"][cv_fn],
                    }
                )

        # Export CSVs and summary JSON
        def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
            if not rows:
                return
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

        _write_csv(out_dir / "skill_extraction_metrics.csv", skill_rows)
        _write_csv(out_dir / "weight_configs_644_pairs.csv", comparison_rows)
        _write_csv(out_dir / "per_jd_ranking_comparison.csv", per_jd_rank_shifts)

        summary_payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ai_service_health": health_info,
            "matching_version": "v2.0-configurable",
            "dataset_readiness": audit_info,
            "skill_extraction_evaluation": skill_summary,
            "weight_configuration_comparison": {
                "configs": config_stats,
                "mae": {
                    "status": "BLOCKED",
                    "reason": "Bộ dữ liệu CV_JD hiện chưa có điểm đánh giá thủ công của con người (Human Ground Truth Score) cho các cặp CV–JD; tuân thủ nguyên tắc không tự tạo điểm giả.",
                },
                "precision_at_5": {
                    "status": "BLOCKED",
                    "reason": "Bộ dữ liệu CV_JD hiện chưa có nhãn phù hợp (Human Relevance Labels) cho các cặp CV–JD; tuân thủ nguyên tắc không tự gán nhãn thay con người.",
                },
                "per_jd_rank_shifts_summary": {
                    "total_jds": len(per_jd_rank_shifts),
                    "top1_changed_base_vs_a": sum(
                        1 for r in per_jd_rank_shifts if r["top1_baseline"] != r["top1_config_a"]
                    ),
                    "top1_changed_base_vs_b": sum(
                        1 for r in per_jd_rank_shifts if r["top1_baseline"] != r["top1_config_b"]
                    ),
                    "avg_top5_overlap_base_vs_a": round(
                        sum(r["top5_overlap_base_vs_a"] for r in per_jd_rank_shifts) / len(per_jd_rank_shifts), 2
                    ),
                    "avg_top5_overlap_base_vs_b": round(
                        sum(r["top5_overlap_base_vs_b"] for r in per_jd_rank_shifts) / len(per_jd_rank_shifts), 2
                    ),
                    "avg_spearman_base_vs_a": round(
                        sum(r["spearman_base_vs_a"] for r in per_jd_rank_shifts) / len(per_jd_rank_shifts), 4
                    ),
                    "avg_spearman_base_vs_b": round(
                        sum(r["spearman_base_vs_b"] for r in per_jd_rank_shifts) / len(per_jd_rank_shifts), 4
                    ),
                },
            },
        }
        (out_dir / "evaluation_summary.json").write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary_payload
    finally:
        archive.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AI skill extraction & configurable weights.")
    parser.add_argument("--ai-url", default=DEFAULT_AI_URL, help="Base URL of live AI Service")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_ZIP_PATH, help="Path to CV_JD zip or extracted dir")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for CSV/JSON results")
    parser.add_argument("--pair-gt", type=Path, default=None, help="Optional CSV with human pair ground truth")
    args = parser.parse_args()

    summary = asyncio.run(run_pipeline(args.ai_url, args.dataset, args.out_dir, args.pair_gt))
    print(json.dumps(summary["skill_extraction_evaluation"], ensure_ascii=False, indent=2))
    print(json.dumps(summary["weight_configuration_comparison"]["per_jd_rank_shifts_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
