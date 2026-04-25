from fastapi import FastAPI

from .extraction import FoglineAnalyzeRequest, FoglineAnalyzeResponse, analyze_plan
from .sample_plans import OPERATION_HARBOR_GLASS


app = FastAPI(title="WARBREAK Backend", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract", response_model=FoglineAnalyzeResponse)
def extract(request: FoglineAnalyzeRequest) -> FoglineAnalyzeResponse:
    return analyze_plan(request)


@app.get("/demo-plan")
def demo_plan() -> dict[str, object]:
    return OPERATION_HARBOR_GLASS

