"""Kiểm thử hàng loạt CV PDF qua luồng Upload (UC-C3) và Nộp đơn (Tuần 8).

Điều kiện: MongoDB, AI Service (8002) và Core Service (8001) đang chạy; đã chạy seed_dev.
Chạy (trong thư mục core-service, đã bật venv):
    python -m scripts.batch_test_cv --dir "C:\\cv_samples" --job-id <ObjectId job OPEN>
Tùy chọn: đặt file expected_skills.json trong thư mục CV: {"ten_file.pdf": ["Python", "Docker"]}
Kết quả: cv_test_report/cv_test_report.csv + cv_test_report/text/<ten_file>.txt
"""
import argparse
import asyncio
import csv
import json
import unicodedata
from pathlib import Path

import httpx

CORE = "http://localhost:8001"
AI = "http://localhost:8002"
PASSWORD = "Test@12345"
REPORT_DIR = Path("cv_test_report")


def garbled_ratio(text: str) -> float:
    """Tỉ lệ ký tự rác (lỗi font/mã hóa) trong văn bản trích xuất."""
    if not text:
        return 0.0
    bad = sum(1 for ch in text if ch == "\ufffd" or unicodedata.category(ch) in ("Co", "Cn", "Cs"))
    return bad / len(text)


async def login(client: httpx.AsyncClient, idx: int) -> str:
    """Mỗi CV một tài khoản ứng viên riêng (bảng applications unique theo job + candidate)."""
    email = f"cvtest_{idx:02d}@example.com"
    await client.post(f"{CORE}/api/v1/auth/register", json={
        "email": email, "password": PASSWORD,
        "full_name": f"CV Test {idx:02d}", "user_type": "CANDIDATE",
    })  # tài khoản đã có thì register báo lỗi -> bỏ qua, đăng nhập luôn
    r = await client.post(f"{CORE}/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


async def test_one(client: httpx.AsyncClient, idx: int, pdf: Path, job_id: str, expected: list) -> dict:
    row = {"file": pdf.name, "size_kb": round(pdf.stat().st_size / 1024), "text_len": "",
           "ai_skills": "", "upload_http": "", "extraction": "", "suggested": "",
           "apply_http": "", "ai_status": "", "score": "", "flags": ""}
    flags = []
    data = pdf.read_bytes()
    detected = []

    # 1) Gọi thẳng AI Service: xem văn bản + skill THÔ để chẩn đoán
    try:
        r = await client.post(f"{AI}/api/v1/ai/parse-cv",
                              files={"file": (pdf.name, data, "application/pdf")})
        if r.status_code == 200:
            j = r.json()
            text, detected = j["parsed_text"], j["skills"]
            row["text_len"], row["ai_skills"] = len(text), len(detected)
            (REPORT_DIR / "text").mkdir(parents=True, exist_ok=True)
            (REPORT_DIR / "text" / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
            if len(text) < 300:
                flags.append("SHORT_TEXT(co the la ban scan)")
            if garbled_ratio(text) > 0.02:
                flags.append("GARBLED_TEXT(loi font)")
            if not detected:
                flags.append("NO_SKILLS")
            elif len(detected) < 3:
                flags.append("FEW_SKILLS")
            have = {x.casefold() for x in detected}
            miss = [s for s in expected if s.casefold() not in have]
            if miss:
                flags.append("MISSING_EXPECTED:" + "|".join(miss))
        else:
            flags.append(f"AI_{r.status_code}:{r.text[:80]}")
    except httpx.HTTPError as e:
        flags.append(f"AI_EXC:{type(e).__name__}")

    # 2) Luồng thật qua Core: login -> upload CV -> nộp đơn
    try:
        token = await login(client, idx)
        headers = {"Authorization": f"Bearer {token}"}

        r = await client.post(f"{CORE}/api/v1/users/me/cv", headers=headers,
                              files={"file": (pdf.name, data, "application/pdf")})
        row["upload_http"] = r.status_code
        if r.status_code == 200:
            ex = r.json()["extraction"]
            row["extraction"] = ex["status"]
            names = [s["name"] for s in ex["suggested_skills"]]
            row["suggested"] = len(names)
            if ex["status"] != "DONE":
                flags.append("EXTRACTION_FAILED")
            lost = [s for s in detected if s.casefold() not in {n.casefold() for n in names}]
            if lost:
                flags.append("UNMAPPED:" + "|".join(lost))   # AI thấy nhưng core không map được
        else:
            flags.append(f"UPLOAD_{r.status_code}")

        r = await client.post(f"{CORE}/api/v1/applications", headers=headers,
                              data={"job_id": job_id},
                              files={"file": (pdf.name, data, "application/pdf")})
        row["apply_http"] = r.status_code
        if r.status_code == 201:
            j = r.json()
            row["ai_status"], row["score"] = j["ai_status"], j["ai_match_score"]
            if j["ai_status"] != "DONE":
                flags.append("APPLY_AI_NOT_DONE")
        elif r.status_code == 409:
            flags.append("ALREADY_APPLIED(chay lai: dung job khac hoac xoa user cvtest_*)")
        else:
            flags.append(f"APPLY_{r.status_code}")
    except httpx.HTTPStatusError as e:
        flags.append(f"CORE_{e.request.url.path}_{e.response.status_code}:{e.response.text[:80]}")
    except httpx.HTTPError as e:
        flags.append(f"CORE_EXC:{type(e).__name__}")

    row["flags"] = "; ".join(flags)
    return row


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Thư mục chứa các file CV .pdf")
    ap.add_argument("--job-id", required=True, help="_id của job đang OPEN")
    args = ap.parse_args()

    folder = Path(args.dir)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"Không thấy file .pdf nào trong {folder}")
    exp_file = folder / "expected_skills.json"
    expected = json.loads(exp_file.read_text(encoding="utf-8")) if exp_file.exists() else {}
    REPORT_DIR.mkdir(exist_ok=True)

    rows = []
    async with httpx.AsyncClient(timeout=120) as client:   # lần đầu AI nạp model nên khá lâu
        for i, pdf in enumerate(pdfs, 1):
            row = await test_one(client, i, pdf, args.job_id, expected.get(pdf.name, []))
            rows.append(row)
            print(f"[{i:02d}/{len(pdfs)}] {pdf.name:<36} {row['flags'] or 'OK'}")

    out = REPORT_DIR / "cv_test_report.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig để Excel đọc đúng
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    bad = [r for r in rows if r["flags"]]
    print(f"\nTổng: {len(rows)} CV | OK: {len(rows) - len(bad)} | Có vấn đề: {len(bad)}")
    print(f"Báo cáo: {out}")


if __name__ == "__main__":
    asyncio.run(main())
