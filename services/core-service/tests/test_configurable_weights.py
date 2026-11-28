import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import fitz
import httpx
import pytest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.application import Application
from app.models.chat import Conversation, Message
from app.models.company import Company
from app.models.job import JobPosting
from app.models.notification import Notification
from app.models.skill import SkillsTaxonomy
from app.models.user import CandidateProfile, User
from app.services import application_service, cv_service
from app.services.job_service import JobService

TEST_DB_NAME = "recruitment_test_configurable_weights"


def _make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), text)
    raw = doc.tobytes()
    doc.close()
    return raw


def _token_for(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role}
    )


def test_configurable_weights_backend_validation_rbac_legacy_and_e2e_snapshot(
    monkeypatch, tmp_path: Path
):
    async def _run():
        mongo_uri_base = settings.MONGO_URI.rsplit("/", 1)[0]
        client_db = AsyncIOMotorClient(f"{mongo_uri_base}/{TEST_DB_NAME}")
        await client_db.drop_database(TEST_DB_NAME)
        db = client_db[TEST_DB_NAME]

        await init_beanie(
            database=db,
            document_models=[
                User,
                Company,
                SkillsTaxonomy,
                JobPosting,
                Application,
                Notification,
                Conversation,
                Message,
            ],
        )

        # Isolate CV file storage to tmp_path
        monkeypatch.setattr(application_service, "CV_DIR", tmp_path)
        monkeypatch.setattr(cv_service, "CV_DIR", tmp_path)

        # Stub embedding generation on JobService so job CRUD doesn't require live port 8002
        async def _fake_job_embed(title, description, skills):
            return [1.0] + [0.0] * 383, "paraphrase-multilingual-MiniLM-L12-v2"

        monkeypatch.setattr(JobService, "generate_job_embedding", staticmethod(_fake_job_embed))

        # Capture exact payloads sent from Core Service -> AI Service and compute real weighted score
        captured_ai_match_requests: list[Dict[str, Any]] = []

        async def _fake_ai_parse(filename: str, data: bytes):
            doc = fitz.open(stream=data, filetype="pdf")
            txt = "\n".join(p.get_text("text") for p in doc).strip()
            doc.close()
            skills = [s for s in ("Python", "FastAPI", "Docker") if s.lower() in txt.lower()]
            return {
                "status": "success",
                "filename": filename,
                "parsed_text": txt,
                "skills": skills,
                "extracted_skills": skills,
                "embedding_vector": [1.0] + [0.0] * 383,
            }

        async def _real_formula_ai_match(
            parsed_text: str,
            candidate_skills: list[str],
            job: JobPosting,
            required_names: list[str],
            candidate_experience_years: float = 0.0,
        ):
            # Intercept httpx.AsyncClient inside application_service._call_ai_match to verify HTTP payload contract!
            raise AssertionError("Should use httpx transport mock below")

        class _MockAITransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                if request.url.path == "/api/v1/ai/parse-cv":
                    return httpx.Response(
                        200,
                        json={
                            "status": "success",
                            "filename": "cv.pdf",
                            "parsed_text": "Python FastAPI developer with 4 years experience",
                            "skills": ["Python", "FastAPI"],
                            "extracted_skills": ["Python", "FastAPI"],
                            "embedding_vector": [1.0] + [0.0] * 383,
                        },
                    )
                if request.url.path == "/api/v1/ai/match":
                    body = json.loads(request.content.decode("utf-8"))
                    captured_ai_match_requests.append(body)
                    weights = body.get("matching_weights") or {
                        "skill_weight": 0.5,
                        "semantic_weight": 0.35,
                        "experience_weight": 0.15,
                    }
                    # Deterministic component scores: skill=90, semantic=80, experience=80
                    skill_s, sem_s, exp_s = 90.0, 80.0, 80.0
                    total_s = round(
                        weights["skill_weight"] * skill_s
                        + weights["semantic_weight"] * sem_s
                        + weights["experience_weight"] * exp_s,
                        1,
                    )
                    req_skills = body.get("required_skills") or []
                    cand_skills = set(body.get("candidate_skills") or [])
                    matched = [s for s in req_skills if s in cand_skills]
                    missing = [s for s in req_skills if s not in cand_skills]
                    breakdown = {
                        "skill_score": skill_s,
                        "semantic_score": sem_s,
                        "experience_score": exp_s,
                        "skill_match": skill_s,
                        "semantic_match": sem_s,
                        "experience_match": exp_s,
                    }
                    return httpx.Response(
                        200,
                        json={
                            "ai_match_score": total_s,
                            "matching_version": "v2.0-configurable",
                            "score_breakdown": breakdown,
                            "matching_weights_snapshot": weights,
                            "embedding_vector": [1.0] + [0.0] * 383,
                            "ai_analysis": {
                                "matched": matched,
                                "missing": missing,
                                "matched_skills": matched,
                                "missing_skills": missing,
                                "score_breakdown": breakdown,
                                "recommendation": f"Điểm {total_s}/100",
                            },
                        },
                    )
                return httpx.Response(404)

        orig_async_client = httpx.AsyncClient

        def _patched_httpx_client(*args, **kwargs):
            kwargs.setdefault("transport", _MockAITransport())
            return orig_async_client(*args, **kwargs)

        monkeypatch.setattr(application_service.httpx, "AsyncClient", _patched_httpx_client)

        try:
            # Seed taxonomy, companies, recruiters, candidates
            py_skill = SkillsTaxonomy(name="Python", category="Backend", aliases=["Python3"])
            fa_skill = SkillsTaxonomy(name="FastAPI", category="Backend", aliases=[])
            dk_skill = SkillsTaxonomy(name="Docker", category="DevOps", aliases=[])
            await py_skill.insert()
            await fa_skill.insert()
            await dk_skill.insert()

            comp1 = Company(name="TechCorp A", verification_status="VERIFIED")
            comp2 = Company(name="TechCorp B", verification_status="VERIFIED")
            await comp1.insert()
            await comp2.insert()

            hr1 = User(
                email="hr1@tech.vn",
                password_hash=hash_password("Pass1234!"),
                full_name="HR One",
                role="USER",
                user_type="RECRUITER",
                company_id=comp1.id,
            )
            hr2 = User(
                email="hr2@tech.vn",
                password_hash=hash_password("Pass1234!"),
                full_name="HR Two",
                role="USER",
                user_type="RECRUITER",
                company_id=comp2.id,
            )
            cand1 = User(
                email="cand1@tech.vn",
                password_hash=hash_password("Pass1234!"),
                full_name="Cand One",
                role="USER",
                user_type="CANDIDATE",
                profile=CandidateProfile(experience=[{"position": "Dev", "years": 4}]),
            )
            cand2 = User(
                email="cand2@tech.vn",
                password_hash=hash_password("Pass1234!"),
                full_name="Cand Two",
                role="USER",
                user_type="CANDIDATE",
                profile=CandidateProfile(experience=[{"position": "Dev", "years": 4}]),
            )
            await hr1.insert()
            await hr2.insert()
            await cand1.insert()
            await cand2.insert()

            hr1_headers = {"Authorization": f"Bearer {_token_for(hr1)}"}
            hr2_headers = {"Authorization": f"Bearer {_token_for(hr2)}"}
            cand1_headers = {"Authorization": f"Bearer {_token_for(cand1)}"}
            cand2_headers = {"Authorization": f"Bearer {_token_for(cand2)}"}

            transport = orig_async_client(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            )
            async with transport as api:
                # 1. Create Job without matching_weights -> default 0.50 / 0.35 / 0.15
                r_default = await api.post(
                    "/api/v1/jobs",
                    headers=hr1_headers,
                    json={
                        "title": "Job Default Weights",
                        "description": "Python FastAPI backend",
                        "required_skills": [str(py_skill.id), str(fa_skill.id)],
                        "experience_required": 2,
                    },
                )
                assert r_default.status_code == 201, r_default.text
                job_def_id = r_default.json()["data"]["_id"] if "_id" in r_default.json()["data"] else r_default.json()["data"]["id"]
                assert r_default.json()["data"]["matching_weights"] == {
                    "skill_weight": 0.5,
                    "semantic_weight": 0.35,
                    "experience_weight": 0.15,
                }

                # 2. Create Job with explicit default weights
                r_exp_def = await api.post(
                    "/api/v1/jobs/managed",
                    headers=hr1_headers,
                    json={
                        "title": "Job Explicit Default",
                        "description": "Python role",
                        "matching_weights": {
                            "skill_weight": 0.5,
                            "semantic_weight": 0.35,
                            "experience_weight": 0.15,
                        },
                    },
                )
                assert r_exp_def.status_code == 201, r_exp_def.text

                # 3. Create Job A (60/25/15) and Job B (40/20/40) -> independent weights
                r_job_a = await api.post(
                    "/api/v1/jobs",
                    headers=hr1_headers,
                    json={
                        "title": "Job A Custom 60-25-15",
                        "description": "Python FastAPI Docker",
                        "required_skills": [str(py_skill.id), str(fa_skill.id), str(dk_skill.id)],
                        "experience_required": 3,
                        "matching_weights": {
                            "skill_weight": 0.6,
                            "semantic_weight": 0.25,
                            "experience_weight": 0.15,
                        },
                    },
                )
                assert r_job_a.status_code == 201, r_job_a.text
                job_a_data = r_job_a.json()["data"]
                job_a_id = job_a_data.get("id") or job_a_data.get("_id")

                r_job_b = await api.post(
                    "/api/v1/jobs",
                    headers=hr1_headers,
                    json={
                        "title": "Job B Senior 40-20-40",
                        "description": "Senior Architect",
                        "matching_weights": {
                            "skill_weight": 0.4,
                            "semantic_weight": 0.2,
                            "experience_weight": 0.4,
                        },
                    },
                )
                assert r_job_b.status_code == 201, r_job_b.text
                job_b_data = r_job_b.json()["data"]
                job_b_id = job_b_data.get("id") or job_b_data.get("_id")

                # Verify independence via GET /my-jobs & GET /managed/{id} & GET /jobs/{id}
                r_my = await api.get("/api/v1/jobs/my-jobs", headers=hr1_headers)
                assert r_my.status_code == 200
                by_id = {j["id"]: j["matching_weights"] for j in r_my.json()["data"]}
                assert by_id[job_a_id] == {"skill_weight": 0.6, "semantic_weight": 0.25, "experience_weight": 0.15}
                assert by_id[job_b_id] == {"skill_weight": 0.4, "semantic_weight": 0.2, "experience_weight": 0.4}
                assert by_id[job_def_id] == {"skill_weight": 0.5, "semantic_weight": 0.35, "experience_weight": 0.15}

                r_pub_a = await api.get(f"/api/v1/jobs/{job_a_id}")
                assert r_pub_a.status_code == 200
                assert r_pub_a.json()["matching_weights"] == {"skill_weight": 0.6, "semantic_weight": 0.25, "experience_weight": 0.15}

                # 4. Validation failures (sum < 100%, sum > 100%, negative, > 100%, missing field, explicit null)
                invalid_payloads = [
                    {"skill_weight": 0.5, "semantic_weight": 0.3, "experience_weight": 0.1},   # < 100%
                    {"skill_weight": 0.6, "semantic_weight": 0.3, "experience_weight": 0.2},   # > 100%
                    {"skill_weight": -0.1, "semantic_weight": 0.6, "experience_weight": 0.5},  # negative
                    {"skill_weight": 1.1, "semantic_weight": 0.0, "experience_weight": 0.0},   # > 100%
                    {"skill_weight": 0.6, "semantic_weight": 0.4},                             # missing field
                ]
                for bad_w in invalid_payloads:
                    r_bad_create = await api.post(
                        "/api/v1/jobs",
                        headers=hr1_headers,
                        json={"title": "Bad", "description": "Bad", "matching_weights": bad_w},
                    )
                    assert r_bad_create.status_code == 422, f"Expected 422 for {bad_w}"

                    r_bad_update = await api.put(
                        f"/api/v1/jobs/{job_a_id}",
                        headers=hr1_headers,
                        json={"matching_weights": bad_w},
                    )
                    assert r_bad_update.status_code == 422

                r_null_update = await api.put(
                    f"/api/v1/jobs/{job_a_id}",
                    headers=hr1_headers,
                    json={"matching_weights": None},
                )
                assert r_null_update.status_code == 422

                # 5. RBAC: Guest (401), Candidate (403), Other Recruiter (403)
                assert (await api.put(f"/api/v1/jobs/{job_a_id}", json={"title": "Hack"})).status_code == 401
                assert (await api.put(f"/api/v1/jobs/{job_a_id}", headers=cand1_headers, json={"title": "Hack"})).status_code == 403
                assert (await api.put(f"/api/v1/jobs/{job_a_id}", headers=hr2_headers, json={
                    "matching_weights": {"skill_weight": 0.2, "semantic_weight": 0.3, "experience_weight": 0.5}
                })).status_code == 403
                assert (await api.get(f"/api/v1/jobs/managed/{job_a_id}", headers=hr2_headers)).status_code == 403

                # 6. Full Integration Flow: Candidate 1 applies to Job A (60/25/15)
                # Even if Candidate tries to sneak in matching_weights in form data, Core ignores it and uses Job A's 60/25/15!
                cv_bytes = _make_pdf("Python FastAPI developer")
                r_apply_1 = await api.post(
                    "/api/v1/applications",
                    headers=cand1_headers,
                    data={
                        "job_id": job_a_id,
                        "matching_weights": '{"skill_weight": 1.0, "semantic_weight": 0.0, "experience_weight": 0.0}',
                    },
                    files={"file": ("cand1.pdf", cv_bytes, "application/pdf")},
                )
                assert r_apply_1.status_code == 201, r_apply_1.text
                app1 = r_apply_1.json()
                assert captured_ai_match_requests[-1]["matching_weights"] == {
                    "skill_weight": 0.6,
                    "semantic_weight": 0.25,
                    "experience_weight": 0.15,
                }
                # 90*0.6 + 80*0.25 + 80*0.15 = 86.0
                assert app1["ai_match_score"] == 86.0
                assert app1["matching_version"] == "v2.0-configurable"
                assert app1["matching_weights_snapshot"] == {
                    "skill_weight": 0.6,
                    "semantic_weight": 0.25,
                    "experience_weight": 0.15,
                }
                assert app1["score_breakdown"]["skill_score"] == 90.0

                # 7. Recruiter updates Job A weights to (20% Skill, 30% Semantic, 50% Experience)
                r_upd_a = await api.put(
                    f"/api/v1/jobs/{job_a_id}",
                    headers=hr1_headers,
                    json={
                        "matching_weights": {
                            "skill_weight": 0.2,
                            "semantic_weight": 0.3,
                            "experience_weight": 0.5,
                        }
                    },
                )
                assert r_upd_a.status_code == 200
                # Partial update without matching_weights keeps the updated 20/30/50 weights
                r_upd_title = await api.patch(
                    f"/api/v1/jobs/{job_a_id}",
                    headers=hr1_headers,
                    json={"title": "Job A Updated Weights"},
                )
                assert r_upd_title.status_code == 200
                assert r_upd_title.json()["matching_weights"] == {
                    "skill_weight": 0.2,
                    "semantic_weight": 0.3,
                    "experience_weight": 0.5,
                }

                # Candidate 2 applies AFTER weights changed -> gets 90*0.2 + 80*0.3 + 80*0.5 = 18 + 24 + 40 = 82.0
                r_apply_2 = await api.post(
                    "/api/v1/applications",
                    headers=cand2_headers,
                    data={"job_id": job_a_id},
                    files={"file": ("cand2.pdf", cv_bytes, "application/pdf")},
                )
                assert r_apply_2.status_code == 201, r_apply_2.text
                app2 = r_apply_2.json()
                assert app2["ai_match_score"] == 82.0
                assert app2["matching_weights_snapshot"] == {
                    "skill_weight": 0.2,
                    "semantic_weight": 0.3,
                    "experience_weight": 0.5,
                }

                # Verify Candidate 1's historical score (86.0) & snapshot (60/25/15) were NOT mutated!
                r_ranked = await api.get(f"/api/v1/jobs/{job_a_id}/applications", headers=hr1_headers)
                assert r_ranked.status_code == 200
                ranked_items = r_ranked.json()
                assert [item["ai_match_score"] for item in ranked_items] == [86.0, 82.0]
                assert ranked_items[0]["matching_weights_snapshot"] == {
                    "skill_weight": 0.6,
                    "semantic_weight": 0.25,
                    "experience_weight": 0.15,
                }
                assert ranked_items[1]["matching_weights_snapshot"] == {
                    "skill_weight": 0.2,
                    "semantic_weight": 0.3,
                    "experience_weight": 0.5,
                }

                # 8. Legacy MongoDB Documents Compatibility (raw insert without matching_weights / snapshot)
                now = datetime.now(timezone.utc)
                raw_legacy_job = await db["job_postings"].insert_one(
                    {
                        "company_id": comp1.id,
                        "recruiter_id": hr1.id,
                        "title": "Legacy Job Without Weights Field",
                        "description": "Legacy Python JD",
                        "required_skills": [py_skill.id],
                        "level": "MID",
                        "experience_required": 1,
                        "status": "OPEN",
                        "views_count": 0,
                        "applications_count": 1,
                        "created_at": now,
                        "updated_at": now,
                        "deleted_at": None,
                    }
                )
                legacy_job_id = str(raw_legacy_job.inserted_id)

                raw_legacy_app = await db["applications"].insert_one(
                    {
                        "job_id": raw_legacy_job.inserted_id,
                        "candidate_id": cand1.id,
                        "cv_url": f"/uploads/cvs/{cand1.id}/legacy.pdf",
                        "pipeline_status": "APPLIED",
                        "status_history": [{"status": "APPLIED", "changed_by": cand1.id, "time": now}],
                        "ai_match_score": 31.3,
                        "matching_version": "v1.0-SBERT",
                        "ai_analysis": {
                            "matched": [py_skill.id],
                            "missing": [],
                            "score_breakdown": {
                                "skill_match": 25.0,
                                "semantic_match": 53.6,
                                "experience_match": 0.0,
                            },
                            "recommendation": "Legacy recommendation",
                        },
                        "applied_at": now,
                        "updated_at": now,
                    }
                )
                legacy_app_id = str(raw_legacy_app.inserted_id)

                # Legacy job works in GET /jobs/{id}, GET /managed/{id}, and when Cand2 applies (uses default 0.5/0.35/0.15 -> 85.0)
                r_leg_detail = await api.get(f"/api/v1/jobs/{legacy_job_id}")
                assert r_leg_detail.status_code == 200
                assert r_leg_detail.json()["matching_weights"] == {
                    "skill_weight": 0.5,
                    "semantic_weight": 0.35,
                    "experience_weight": 0.15,
                }

                r_leg_apply = await api.post(
                    "/api/v1/applications",
                    headers=cand2_headers,
                    data={"job_id": legacy_job_id},
                    files={"file": ("cand2_leg.pdf", cv_bytes, "application/pdf")},
                )
                assert r_leg_apply.status_code == 201, r_leg_apply.text
                assert r_leg_apply.json()["ai_match_score"] == 85.0
                assert r_leg_apply.json()["matching_weights_snapshot"] == {
                    "skill_weight": 0.5,
                    "semantic_weight": 0.35,
                    "experience_weight": 0.15,
                }

                # Legacy application without snapshot still loads cleanly for both Candidate and Recruiter
                r_leg_app = await api.get(f"/api/v1/applications/{legacy_app_id}", headers=cand1_headers)
                assert r_leg_app.status_code == 200, r_leg_app.text
                leg_json = r_leg_app.json()
                assert leg_json["ai_match_score"] == 31.3
                assert leg_json["matching_version"] == "v1.0-SBERT"
                assert leg_json["matching_weights_snapshot"] is None
                assert leg_json["score_breakdown"] == {
                    "skill_match": 25.0,
                    "semantic_match": 53.6,
                    "experience_match": 0.0,
                }

                r_leg_ranked = await api.get(f"/api/v1/jobs/{legacy_job_id}/applications", headers=hr1_headers)
                assert r_leg_ranked.status_code == 200
                assert len(r_leg_ranked.json()) == 2
        finally:
            await client_db.drop_database(TEST_DB_NAME)
            client_db.close()

    asyncio.run(_run())
