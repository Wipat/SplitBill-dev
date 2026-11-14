from api.balances import router as balances_router
from api.expenses import router as expenses_router
from api.groups import router as groups_router
from fastapi import FastAPI

app = FastAPI(title="Splitbill API")
app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(balances_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
