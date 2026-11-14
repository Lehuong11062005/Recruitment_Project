import asyncio, os, sys
os.environ["JWT_SECRET_KEY"]="test-secret"
sys.path.insert(0,".")
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks
from app.models.user import User
from app.models.company import Company
from app.models.skill import SkillsTaxonomy
from app.models.job import JobPosting
from app.models.application import Application
from app.models.notification import Notification
from app.models.chat import Conversation, Message
from app.core.security import create_access_token
from app.main import app
from app.services import notification_service, email_service

sent=[]
email_service.send_email = lambda *a, **k: sent.append(a) or True   # không gửi thật

async def setup():
    db = AsyncMongoMockClient()["recruitment_test"]
    await init_beanie(database=db, document_models=[User,Company,SkillsTaxonomy,JobPosting,Application,Notification,Conversation,Message])
    comp = Company(name="ACME"); await comp.insert()
    hr = User(email="hr@x.com", password_hash="x", full_name="HR An", user_type="RECRUITER", company_id=comp.id); await hr.insert()
    hr2 = User(email="hr2@x.com", password_hash="x", full_name="HR Khac", user_type="RECRUITER", company_id=comp.id); await hr2.insert()
    c = User(email="c@x.com", password_hash="x", full_name="Cuong", user_type="CANDIDATE"); await c.insert()
    c2 = User(email="c2@x.com", password_hash="x", full_name="Nguoi La", user_type="CANDIDATE"); await c2.insert()
    job = JobPosting(company_id=comp.id, recruiter_id=hr.id, title="Backend Dev", description="d"); await job.insert()
    ap = Application(job_id=job.id, candidate_id=c.id, cv_url="/x.pdf",
                     interview_schedule={"time":"09:00 20/11/2026","location":"HCM","note":"Mang CCCD"}, pipeline_status="INTERVIEW"); await ap.insert()
    return hr, hr2, c, c2, job, ap

hr, hr2, c, c2, job, ap = asyncio.run(setup())
tok = lambda u: {"Authorization": f"Bearer {create_access_token({'sub': str(u.id)})}"}
raw = lambda u: create_access_token({'sub': str(u.id)})
client = TestClient(app)

# ---- Notifications ----
async def fire():
    bt = BackgroundTasks()
    n1 = await notification_service.notify_application_status(ap, bt)
    n2 = await notification_service.notify_interview_schedule(ap, bt)
    for t in bt.tasks: t.func(*t.args, **t.kwargs)
    return n1, n2
n1, n2 = asyncio.run(fire())
assert n1 and n1.type=="APPLICATION_STATUS" and n1.is_read is False and "Mang CCCD" in n1.content
assert len(sent)==2 and sent[0][0]=="c@x.com", sent
r = client.get("/api/v1/notifications", headers=tok(c)); assert r.status_code==200, r.text
d = r.json(); assert len(d)==2 and d[0]["created_at"].endswith("Z") and d[0]["created_at"]>=d[1]["created_at"]
nid = d[0]["id"]
assert client.get("/api/v1/notifications", headers=tok(hr)).json()==[]          # HR không thấy của người khác
assert client.patch(f"/api/v1/notifications/{nid}/read", headers=tok(hr)).status_code==404
r = client.patch(f"/api/v1/notifications/{nid}/read", headers=tok(c)); assert r.json()["is_read"] is True
assert len(client.get("/api/v1/notifications?unread_only=true", headers=tok(c)).json())==1
assert client.get("/api/v1/notifications").status_code==401
print("notifications OK")

# ---- Chat REST ----
jid=str(job.id)
r = client.post("/api/v1/conversations", json={"job_id": jid}, headers=tok(c)); assert r.status_code==200, r.text
conv = r.json(); assert conv["other_user"]["full_name"]=="HR An" and conv["job_title"]=="Backend Dev"
r2 = client.post("/api/v1/conversations", json={"job_id": jid, "candidate_id": str(c.id)}, headers=tok(hr)); assert r2.json()["id"]==conv["id"]
assert client.post("/api/v1/conversations", json={"job_id": jid}, headers=tok(hr)).status_code==422
assert client.post("/api/v1/conversations", json={"job_id": jid, "candidate_id": str(c2.id)}, headers=tok(hr)).status_code==403
assert client.post("/api/v1/conversations", json={"job_id": jid, "candidate_id": str(c.id)}, headers=tok(hr2)).status_code==403
cid=conv["id"]

# ---- WebSocket ----
with client.websocket_connect(f"/ws/chat/{cid}?token={raw(c)}") as ws_c, \
     client.websocket_connect(f"/ws/chat/{cid}?token={raw(hr)}") as ws_h:
    ws_c.send_json({"message_type":"TEXT","content":"Chào anh, em muốn hỏi về vị trí này"})
    m1 = ws_c.receive_json(); m2 = ws_h.receive_json()
    assert m1==m2 and m1["event"]=="message" and m1["data"]["sender_role"]=="CANDIDATE" and m1["data"]["is_read"] is False
    ws_h.send_json({"event":"message","content":"Chào em"}); ws_h.receive_json(); ws_c.receive_json()
    ws_c.send_json({"content":"   "}); assert ws_c.receive_json()["event"]=="error"
    ws_c.send_json({"message_type":"FILE","content":"","attachments":["javascript:alert(1)"]}); assert ws_c.receive_json()["event"]=="error"
    ws_c.send_json({"message_type":"FILE","content":"","attachments":["/uploads/cv.pdf"]}); ws_c.receive_json(); ws_h.receive_json()
    ws_c.send_text("khong phai json"); assert ws_c.receive_json()["event"]=="error"
    ws_c.send_json({"event":"ping"}); assert ws_c.receive_json()=={"event":"pong"}
    ws_h.send_json({"event":"read"}); ev=ws_h.receive_json(); assert ev["event"]=="read"; ws_c.receive_json()
print("ws chat OK")

# từ chối kết nối
from starlette.websockets import WebSocketDisconnect
for tk, code in [("bad", 4401), (raw(c2), 4404)]:
    try:
        with client.websocket_connect(f"/ws/chat/{cid}?token={tk}") as ws:
            ws.receive_json()
        raise SystemExit("phải bị đóng")
    except WebSocketDisconnect as e:
        assert e.code==code, (tk, e.code)
print("ws auth OK")

# ---- lịch sử + last_message + unread ----
lst = client.get("/api/v1/conversations", headers=tok(c)).json()
assert lst[0]["last_message"]=="[Tệp đính kèm]", lst
hr_list = client.get("/api/v1/conversations", headers=tok(hr)).json()
print("unread HR trước khi mở:", hr_list[0]["unread_count"])
msgs = client.get(f"/api/v1/conversations/{cid}/messages", headers=tok(hr)).json()
assert [m["content"] for m in msgs][:2]==["Chào anh, em muốn hỏi về vị trí này","Chào em"], msgs
assert client.get(f"/api/v1/conversations/{cid}/messages?limit=1", headers=tok(hr)).json()[0]["message_type"]=="FILE"
assert client.get("/api/v1/conversations", headers=tok(hr)).json()[0]["unread_count"]==0
assert client.get(f"/api/v1/conversations/{cid}/messages", headers=tok(c2)).status_code==404
assert client.get(f"/api/v1/conversations/{cid}/messages?before={msgs[-1]['created_at']}", headers=tok(c)).status_code==200
print("ALL OK")
