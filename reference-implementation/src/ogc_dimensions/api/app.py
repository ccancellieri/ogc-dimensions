"""OGC Dimensions Reference Implementation API.

FastAPI application demonstrating the generator specification:
  /dimensions                              -- list registered dimensions
  /dimensions/{dimension_id}/generate      -- paginated member generation
  /dimensions/{dimension_id}/extent        -- dimension boundaries
  /dimensions/{dimension_id}/inverse       -- value-to-coordinate mapping
  /dimensions/{dimension_id}/search        -- find members by query

Run: uvicorn ogc_dimensions.api.app:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="OGC Dimensions Reference Implementation",
    description=(
        "Reference implementation for the OGC Dimensions specification: "
        "paginated dimension members, algorithmic generators, "
        "bijective inversion, and search capabilities."
    ),
    version="0.1.0",
    license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/dimensions")


@app.get("/")
async def root(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "title": "OGC Dimensions Reference Implementation",
        "description": "Reference implementation for scalable dimension member dissemination and algorithmic generation.",
        "links": [
            {"rel": "self", "href": f"{base}/", "type": "application/json"},
            {"rel": "service-desc", "href": f"{base}/openapi.json", "type": "application/json"},
            {"rel": "service-doc", "href": f"{base}/docs", "type": "text/html"},
            {
                "rel": "dimensions",
                "href": f"{base}/dimensions",
                "type": "application/json",
                "title": "Registered dimensions and their generators",
            },
        ],
        "conformsTo": [
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/basic",
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/invertible",
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/searchable",
        ],
    }
