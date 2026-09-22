"""gbp_mcp: read-only Google Business Profile MCP server.

Every tool is a thin call to the Pipedream GBP proxy, which holds the Google OAuth.
This server holds only the proxy key. Deployed on Cloud Run, streamable HTTP, stateless.
"""

import json
import os
import re
from datetime import date, timedelta
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

PROXY_URL = os.environ["GBP_PROXY_URL"]
PROXY_KEY = os.environ["GBP_PROXY_KEY"]
MCP_TOKEN = os.environ.get("MCP_BEARER_TOKEN")  # optional client auth
LAG_DAYS = int(os.environ.get("GBP_LAG_DAYS", "5"))

mcp = FastMCP("gbp_mcp", stateless_http=True, json_response=True, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

LOCATION_RE = re.compile(r"^locations/\d+$")
YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YM_RE = re.compile(r"^\d{4}-\d{2}$")


# ---------------------------------------------------------------- proxy call
async def call_proxy(op: str, **body) -> dict:
    payload = {"op": op, **{k: v for k, v in body.items() if v is not None}}
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(
                PROXY_URL,
                json=payload,
                headers={"x-gbp-proxy-key": PROXY_KEY, "Content-Type": "application/json"},
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Proxy unreachable: {e}. Check GBP_PROXY_URL and that the Pipedream workflow is deployed.")
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"Proxy returned non-JSON (HTTP {r.status_code}): {r.text[:300]}")
    if r.status_code != 200 or not data.get("ok"):
        err = data.get("error", "unknown error")
        hints = {
            401: "Proxy key mismatch. GBP_PROXY_KEY on this server must equal the Pipedream secret.",
            404: "Location not found under the connected Google account. Run gbp_list_locations to see valid IDs.",
            403: "Google denied access. The connected account may have lost manager rights on this profile.",
        }
        raise RuntimeError(f"Proxy error {r.status_code}: {err}. {hints.get(r.status_code, '')}".strip())
    return data


def out(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


# ---------------------------------------------------------------- inputs
class LocationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    location_id: str = Field(..., description="GBP location resource name, e.g. 'locations/14620019306909596262'. Get from gbp_list_locations.")

    @field_validator("location_id")
    @classmethod
    def _loc(cls, v):
        if not LOCATION_RE.match(v):
            raise ValueError("location_id must look like locations/1234567890")
        return v


class DailyMetricsInput(LocationInput):
    start_date: str = Field(..., description="YYYY-MM-DD (inclusive)")
    end_date: str = Field(..., description="YYYY-MM-DD (inclusive). Data lags 3-5 days; use gbp_get_data_freshness for the safe cutoff.")
    metrics: Optional[list[str]] = Field(default=None, description="Optional subset. Default: all 9 (4 impression surfaces, CALL_CLICKS, WEBSITE_CLICKS, BUSINESS_DIRECTION_REQUESTS, BUSINESS_CONVERSATIONS, BUSINESS_BOOKINGS).")

    @field_validator("start_date", "end_date")
    @classmethod
    def _ymd(cls, v):
        if not YMD_RE.match(v):
            raise ValueError("dates must be YYYY-MM-DD")
        return v


class SearchKeywordsInput(LocationInput):
    start_month: str = Field(..., description="YYYY-MM (inclusive)")
    end_month: str = Field(..., description="YYYY-MM (inclusive). The current month is incomplete; prefer the previous full month.")

    @field_validator("start_month", "end_month")
    @classmethod
    def _ym(cls, v):
        if not YM_RE.match(v):
            raise ValueError("months must be YYYY-MM")
        return v


class ReviewsInput(LocationInput):
    account_id: Optional[str] = Field(default=None, description="'accounts/123...' from gbp_list_locations. Optional but saves several API calls.")
    max_reviews: int = Field(default=200, ge=1, le=1000, description="Most-recent reviews to return.")


class MediaPostsInput(LocationInput):
    account_id: Optional[str] = Field(default=None, description="'accounts/123...' from gbp_list_locations. Optional.")


class FreshnessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weeks: int = Field(default=13, ge=1, le=52, description="How many full weeks of history the window should cover.")
    lag_days: Optional[int] = Field(default=None, ge=0, le=30, description="Days to cut off the end of the window for Google's reporting lag. The gbp-maa skill owns this value (currently 8: impressions finish posting ~8 days out, actions sooner). Omit to use the server default.")


RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}


# ---------------------------------------------------------------- tools
@mcp.tool(name="gbp_list_locations", annotations={"title": "List GBP locations", **RO})
async def gbp_list_locations() -> str:
    """List every Google Business Profile location the connected account can manage.

    Returns account_id, location_id, title, primary category, city/state, website, maps_uri, place_id.
    Use this first to resolve a client name to its location_id. Clients with several
    locations (franchises, multi-office firms) appear once per location; always key
    analysis by location_id, never by title.
    """
    return out((await call_proxy("list_locations"))["data"])


@mcp.tool(name="gbp_get_data_freshness", annotations={"title": "Safe reporting window", **RO})
async def gbp_get_data_freshness(params: FreshnessInput) -> str:
    """Compute the date window an MAA should use, accounting for GBP's reporting lag.

    GBP Performance data is incomplete for the most recent days (impressions post
    later than actions). Pass lag_days from the skill; this returns end_date = today - lag, and start_date covering the requested number of full weeks
    ending on that date, plus the aligned previous period for comparison. Call this
    before gbp_get_daily_metrics so every run uses the same cutoff rule.
    """
    lag = params.lag_days if params.lag_days is not None else LAG_DAYS
    today = date.today()
    end = today - timedelta(days=lag)
    start = end - timedelta(days=params.weeks * 7 - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=params.weeks * 7 - 1)
    return out({
        "today": today.isoformat(),
        "lag_days": lag,
        "current_period": {"start_date": start.isoformat(), "end_date": end.isoformat(), "days": params.weeks * 7},
        "previous_period": {"start_date": prev_start.isoformat(), "end_date": prev_end.isoformat(), "days": params.weeks * 7},
        "last_full_month": (end.replace(day=1) - timedelta(days=1)).strftime("%Y-%m"),
        "note": f"Days after {end.isoformat()} are excluded because Google has not finished reporting them.",
    })


@mcp.tool(name="gbp_get_daily_metrics", annotations={"title": "Daily performance metrics", **RO})
async def gbp_get_daily_metrics(params: DailyMetricsInput) -> str:
    """Daily GBP Performance metrics for one location over a date range.

    Returns totals per metric plus one row per (date, metric). Impressions come in four
    surfaces (desktop/mobile x maps/search). Actions: CALL_CLICKS, WEBSITE_CLICKS,
    BUSINESS_DIRECTION_REQUESTS, BUSINESS_CONVERSATIONS, BUSINESS_BOOKINGS.
    Verified against the GBP dashboard: action counts match exactly; the dashboard's
    impressions figure is per-user deduplicated and may read lower than the API sum.
    """
    return out((await call_proxy(
        "daily_metrics",
        location_id=params.location_id,
        start_date=params.start_date,
        end_date=params.end_date,
        metrics=params.metrics,
    ))["data"])


@mcp.tool(name="gbp_get_search_keywords", annotations={"title": "Search keywords", **RO})
async def gbp_get_search_keywords(params: SearchKeywordsInput) -> str:
    """Monthly search keywords that surfaced this location, with impression counts.

    Sorted by impressions descending. Low-volume terms have impressions=null and
    below_threshold set (Google withholds exact counts under that threshold); report
    those as "fewer than N", not as zero.
    """
    return out((await call_proxy(
        "search_keywords",
        location_id=params.location_id,
        start_month=params.start_month,
        end_month=params.end_month,
    ))["data"])


@mcp.tool(name="gbp_get_reviews", annotations={"title": "Reviews", **RO})
async def gbp_get_reviews(params: ReviewsInput) -> str:
    """Reviews for one location: average_rating and total_review_count for the whole
    profile, plus the most recent reviews (rating, comment, reviewer, created_at,
    has_reply, reply_at). Use created_at to compute review velocity per period and
    has_reply for reply coverage. 'truncated' is true when more exist than returned.
    """
    return out((await call_proxy(
        "reviews",
        location_id=params.location_id,
        account_id=params.account_id,
        max_reviews=params.max_reviews,
    ))["data"])


@mcp.tool(name="gbp_get_profile", annotations={"title": "Profile details", **RO})
async def gbp_get_profile(params: LocationInput) -> str:
    """Current profile state: title, categories, phone, address, website, regular and
    special hours, service area, service items, description, open status, attributes.
    This is a snapshot of now. To detect changes over time, save it to the client
    ledger each run and diff against the previous snapshot.
    """
    return out((await call_proxy("profile", location_id=params.location_id))["data"])


@mcp.tool(name="gbp_get_media_posts", annotations={"title": "Photos and posts", **RO})
async def gbp_get_media_posts(params: MediaPostsInput) -> str:
    """Photo inventory (total count, latest upload date, counts by format) and recent
    Google Posts (latest post date, last 10 summaries). A stale latest_created_at on
    either is an activity signal worth calling out in the MAA.
    """
    return out((await call_proxy(
        "media_posts",
        location_id=params.location_id,
        account_id=params.account_id,
    ))["data"])


# ---------------------------------------------------------------- auth + app
class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/healthz":
            return JSONResponse({"ok": True})
        if MCP_TOKEN:
            auth = request.headers.get("authorization", "")
            if auth != f"Bearer {MCP_TOKEN}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BearerAuth)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
