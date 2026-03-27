"""OGC Dimensions Testbed API.

FastAPI application demonstrating the generator specification:
  /generators/{type}/generate  -- paginated member generation
  /generators/{type}/extent    -- dimension boundaries
  /generators/{type}/inverse   -- value-to-coordinate mapping
  /generators/{type}/search    -- find members by query

Run: uvicorn testbed.api.app:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="OGC Dimensions Testbed",
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

app.include_router(router, prefix="/generators")


@app.get("/")
async def root():
    return {
        "title": "OGC Dimensions Testbed",
        "description": "Reference implementation for scalable dimension member dissemination and algorithmic generation.",
        "links": [
            {"rel": "self", "href": "/", "type": "application/json"},
            {"rel": "service-desc", "href": "/openapi.json", "type": "application/json"},
            {"rel": "service-doc", "href": "/docs", "type": "text/html"},
            {
                "rel": "generators",
                "href": "/generators",
                "type": "application/json",
                "title": "Available dimension generators",
            },
        ],
        "conformsTo": [
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/basic",
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/invertible",
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/searchable",
        ],
    }
