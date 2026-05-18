"""OGC Dimensions Reference Implementation API.

FastAPI application demonstrating the OGC Dimensions specification:
  /dimensions                              -- list registered dimensions
  /dimensions/{dimension_id}/items         -- paginated members (OGC Records /items)
  /dimensions/{dimension_id}/extent        -- dimension boundaries
  /dimensions/{dimension_id}/inverse       -- value-to-coordinate mapping
  /dimensions/{dimension_id}/search        -- find members by query

Run: uvicorn ogc_dimensions.api.app:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import DIMENSIONS, router


def _assert_extent_consistent_with_generator() -> None:
    """dimension-collection BB §"Extent derivation" — fail loud at startup
    if any provider's reported extent disagrees with its generator size.
    """
    for dim_id, cfg in DIMENSIONS.items():
        if not (cfg.extent_min and cfg.extent_max):
            continue
        ext = cfg.provider.extent(cfg.extent_min, cfg.extent_max)
        page = cfg.provider.generate(cfg.extent_min, cfg.extent_max, limit=1, offset=0)
        if ext.size != page.number_matched:
            raise RuntimeError(
                f"Dimension '{dim_id}': extent.size={ext.size} disagrees "
                f"with generator number_matched={page.number_matched}. "
                f"Extent MUST be derived from the generator (issue #5)."
            )

app = FastAPI(
    title="OGC Dimensions Reference Implementation",
    description=(
        "Reference implementation for the OGC Dimensions specification: "
        "paginated dimension members, algorithmic generators, "
        "invertible generators, search capabilities, and hierarchical dimensions "
        "(/children, /ancestors) aligned with the STAC API Children Extension."
    ),
    version="0.2.0",
    license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/dimensions")

_assert_extent_consistent_with_generator()


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
            "https://ccancellieri.github.io/ogc-dimensions/spec/conformance/hierarchical",
        ],
    }
