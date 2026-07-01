import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

# StaticPool forces all engine.connect() calls to share ONE underlying SQLite
# connection, so tables created by create_all are visible to every session.
SQLITE_URL = "sqlite://"
engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    import app.models  # noqa: F401 — registers User + RefreshTokenBlocklist with Base
    import app.models.b2b  # noqa: F401
    import app.models.session  # noqa: F401
    import app.models.intake  # noqa: F401
    import app.models.response  # noqa: F401
    import app.models.score  # noqa: F401
    import app.models.report  # noqa: F401
    import app.models.bias_flag  # noqa: F401
    import app.models.section_timer  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Direct DB session for test setup (e.g. inserting users)."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """TestClient with per-request DB sessions backed by the test engine."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    import app.routers.sessions as sessions_router
    original_factory = sessions_router._db_factory
    sessions_router._db_factory = TestingSessionLocal

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    sessions_router._db_factory = original_factory
