"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_candidate_repository,
    get_tenant_config_repository,
    get_user_signal_repository,
)
from app.main import app
from app.models.schemas import TenantRankingRules, UserSignals, VideoMetadata
from app.repositories.memory import (
    InMemoryCandidateRepository,
    InMemoryTenantConfigRepository,
    InMemoryUserSignalRepository,
)


@pytest.fixture
def mock_user_signal_repo():
    """Fixture for mocked UserSignalRepository."""
    repo = InMemoryUserSignalRepository()
    return repo


@pytest.fixture
def mock_candidate_repo():
    """Fixture for mocked CandidateRepository."""
    repo = InMemoryCandidateRepository()
    return repo


@pytest.fixture
def mock_tenant_config_repo():
    """Fixture for mocked TenantConfigRepository."""
    repo = InMemoryTenantConfigRepository()
    return repo


@pytest.fixture
def test_client(
    mock_user_signal_repo,
    mock_candidate_repo,
    mock_tenant_config_repo,
):
    """
    TestClient fixture with dependency overrides.
    Uses in-memory repositories for isolation.
    """
    app.dependency_overrides[get_user_signal_repository] = lambda: mock_user_signal_repo
    app.dependency_overrides[get_candidate_repository] = lambda: mock_candidate_repo
    app.dependency_overrides[
        get_tenant_config_repository
    ] = lambda: mock_tenant_config_repo

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_video():
    """Fixture for a standard video metadata object."""
    return VideoMetadata(
        id="v1",
        title="Test Video",
        score=80.0,
        tags=["sports"],
        maturity_rating="G",
        published_at=1700000000,
    )


@pytest.fixture
def sample_user_signals():
    """Fixture for standard user signals."""
    return UserSignals(
        user_hash="user_test",
        watched_ids=[],
        affinities={"sports": 1.0},
    )


@pytest.fixture
def sample_config():
    """Fixture for tenant configuration."""
    return TenantRankingRules(
        tenant_id="tenant_test",
        boost_weights={"recency": 1.0, "popularity": 1.0, "user_affinity": 1.0},
    )
