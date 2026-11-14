from api.balances import router as balances_router
from api.expenses import router as expenses_router
from api.groups import router as groups_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Splitbill API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(balances_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
