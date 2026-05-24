from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.db.models.final_signal import FinalSignal
from app.main import app
from app.security.auth import CURTIS_USER, create_access_token


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(CURTIS_USER)}"}


def _seed_signal(db: Session, transcript_id: str = "t-1", **overrides) -> FinalSignal:
    from app.db.models.transcript import Transcript

    if not db.get(Transcript, transcript_id):
        db.add(Transcript(id=transcript_id, title="Test", raw_text="x", status="completed"))
        db.flush()

    defaults = dict(
        transcript_id=transcript_id,
        item_type="driver",
        rank=1,
        category="Test category",
        advisor_quote="Some quote.",
        timestamp="00:01:00",
        evidence_strength="explicit",
        rationale="Test rationale.",
    )
    defaults.update(overrides)
    signal = FinalSignal(**defaults)
    db.add(signal)
    db.commit()
    return signal


def test_patch_signal_approve(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            signal = _seed_signal(db)
            signal_id = signal.id

        client = TestClient(app)
        headers = auth_headers()
        response = client.patch(
            f"/review/signals/{signal_id}",
            headers=headers,
            json={"review_status": "approved"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["signal_id"] == signal_id
        assert body["review_status"] == "approved"
        assert body["reviewed_by"] == CURTIS_USER.username
        assert body["reviewed_at"] is not None
    finally:
        app.dependency_overrides.clear()


def test_patch_signal_reject(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            signal = _seed_signal(db)
            signal_id = signal.id

        client = TestClient(app)
        headers = auth_headers()
        response = client.patch(
            f"/review/signals/{signal_id}",
            headers=headers,
            json={"review_status": "rejected", "reviewer_notes": "Not relevant"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["review_status"] == "rejected"
        assert body["reviewer_notes"] == "Not relevant"
    finally:
        app.dependency_overrides.clear()


def test_patch_signal_flag(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            signal = _seed_signal(db)
            signal_id = signal.id

        client = TestClient(app)
        headers = auth_headers()
        response = client.patch(
            f"/review/signals/{signal_id}",
            headers=headers,
            json={"flag": True},
        )
        assert response.status_code == 200
        assert response.json()["flag"] is True
    finally:
        app.dependency_overrides.clear()


def test_patch_signal_not_found(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        headers = auth_headers()
        response = client.patch(
            "/review/signals/nonexistent-id",
            headers=headers,
            json={"review_status": "approved"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_bulk_update(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            s1 = _seed_signal(db, id="sig-1")
            s2 = _seed_signal(db, id="sig-2", rank=2)
            s1_id = s1.id
            s2_id = s2.id

        client = TestClient(app)
        headers = auth_headers()
        response = client.patch(
            "/review/signals",
            headers=headers,
            json={
                "signal_ids": [s1_id, s2_id, "missing-id"],
                "review_status": "approved",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["updated"]) == 2
        assert body["not_found"] == ["missing-id"]
        assert all(u["review_status"] == "approved" for u in body["updated"])
    finally:
        app.dependency_overrides.clear()


def test_signals_list_returns_review_fields(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            _seed_signal(db)

        client = TestClient(app)
        headers = auth_headers()

        client.patch(
            f"/review/signals/{_get_first_signal_id(client, headers)}",
            headers=headers,
            json={"review_status": "approved", "flag": True},
        )

        signals = client.get("/signals", headers=headers).json()
        assert len(signals) >= 1
        sig = signals[0]
        assert "review_status" in sig
        assert "flag" in sig
        assert sig["review_status"] == "approved"
        assert sig["flag"] is True
    finally:
        app.dependency_overrides.clear()


def test_feedback_persists_across_requests(db_session_factory: sessionmaker[Session]) -> None:
    def override_get_db() -> Iterator[Session]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with db_session_factory() as db:
            signal = _seed_signal(db)
            signal_id = signal.id

        client = TestClient(app)
        headers = auth_headers()

        client.patch(
            f"/review/signals/{signal_id}",
            headers=headers,
            json={"review_status": "rejected"},
        )

        signals = client.get("/signals", headers=headers).json()
        matching = [s for s in signals if s["id"] == signal_id]
        assert len(matching) == 1
        assert matching[0]["review_status"] == "rejected"
    finally:
        app.dependency_overrides.clear()


def _get_first_signal_id(client: TestClient, headers: dict[str, str]) -> str:
    signals = client.get("/signals", headers=headers).json()
    return signals[0]["id"]
