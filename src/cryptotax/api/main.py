import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from cryptotax.api.accounts import router as accounts_router
from cryptotax.api.analytics import router as analytics_router
from cryptotax.api.entities import router as entities_router
from cryptotax.api.errors import router as errors_router
from cryptotax.api.imports import router as imports_router
from cryptotax.api.journal import router as journal_router
from cryptotax.api.parser import router as parser_router
from cryptotax.api.reports import router as reports_router
from cryptotax.api.tax import router as tax_router
from cryptotax.api.transactions import router as transactions_router
from cryptotax.api.wallets import router as wallets_router
from cryptotax.container import Container

logger = logging.getLogger("cryptotax.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container()
    app.state.container = container
    yield
    engine = container.engine()
    await engine.dispose()


app = FastAPI(title="LeafJots", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.error("Unhandled error on %s %s:\n%s", request.method, request.url.path, "".join(tb))
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)
app.include_router(entities_router)
app.include_router(wallets_router)
app.include_router(transactions_router)
app.include_router(parser_router)
app.include_router(journal_router)
app.include_router(accounts_router)
app.include_router(errors_router)
app.include_router(tax_router)
app.include_router(reports_router)
app.include_router(imports_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
