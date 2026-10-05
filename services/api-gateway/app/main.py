from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.proxy.ai_proxy import router as ai_router
from app.proxy.core_proxy import router as core_router
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"] 
)

app.include_router(core_router,prefix="/api")
app.include_router(ai_router,prefix="/ai")

@app.get("/")
def root():
    return {"messager": "Api-gateway is running"}

