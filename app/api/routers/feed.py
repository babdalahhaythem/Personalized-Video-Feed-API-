"""
Feed API router.
Implements GET /v1/feed endpoint with proper error handling and headers.
"""
import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.dependencies import get_feed_service
from app.config import get_settings
from app.models.schemas import FeedResponse
from app.services.feed import FeedService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["feed"])


@router.get(
    "/feed",
    response_model=FeedResponse,
    summary="Get Personalized Feed",
    description="""
    Retrieve a personalized video feed for the specified user.

    The endpoint applies rule-based ranking based on:
    - User watch history and category affinities
    - Tenant-specific boost weights
    - Recency and popularity factors

    **Features:**
    - Cursor-based pagination for infinite scroll
    - Graceful degradation to trending feed on failure
    - Feature flag controlled with kill switch
    """,
    responses={
        200: {"description": "Ranked feed returned successfully"},
        304: {"description": "Feed not modified"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal error - returns fallback feed"},
    },
)
async def get_feed(
    response: Response,
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Number of items to return",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Pagination cursor from previous response",
    ),
    user_hash: str = Query(
        ...,
        min_length=1,
        description="Anonymized user identifier",
    ),
    x_tenant_id: str = Header(
        default="tenant_sports",
        alias="X-Tenant-ID",
        description="Tenant identifier",
    ),
    if_none_match: Optional[str] = Header(
        default=None,
        description="ETag from previous response",
    ),
    feed_service: FeedService = Depends(get_feed_service),
) -> FeedResponse:
    """
    Get personalized feed endpoint.

    This is the main SDK-facing endpoint for retrieving ranked video content.
    """
    settings = get_settings()

    # Enforce limit from settings
    effective_limit = min(limit, settings.MAX_FEED_LIMIT)

    # Call feed service
    feed_response = await feed_service.get_feed(
        tenant_id=x_tenant_id,
        user_hash=user_hash,
        limit=effective_limit,
        cursor=cursor,
    )

    # -------------------------------------------------------------------------
    # ETag / 304 Logic
    # -------------------------------------------------------------------------
    etag: Optional[str] = None
    if feed_response.items:
        # Calculate weak ETag based on item IDs
        content_str = "".join([item.id for item in feed_response.items])
        etag_hash = hashlib.md5(content_str.encode()).hexdigest()[:16]
        etag = f'W/"{etag_hash}"'
        response.headers["ETag"] = etag

    # Check for cache hit
    if if_none_match and etag and if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # -------------------------------------------------------------------------
    # Cache-Control Logic
    # -------------------------------------------------------------------------
    # 1. Personalized (Standard): Private, short TTL
    if feed_response.is_personalized and not feed_response.degraded:
        response.headers["Cache-Control"] = "private, max-age=30"
        response.headers["Vary"] = "X-User-Hash"
    
    # 2. Fallback / Degraded: Public, short TTL + SWR
    else:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=15"
        # Public cache should NOT vary by User Hash
        response.headers["Vary"] = "Accept-Encoding"

    # Debug header
    response.headers["X-Personalized"] = str(feed_response.is_personalized).lower()

    return feed_response
