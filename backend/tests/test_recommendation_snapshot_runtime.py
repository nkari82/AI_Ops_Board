from __future__ import annotations

import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if "pgvector" not in sys.modules:
    from sqlalchemy.types import UserDefinedType

    pgvector_mod = types.ModuleType("pgvector")
    sqlalchemy_mod = types.ModuleType("pgvector.sqlalchemy")

    class Vector(UserDefinedType):
        def __init__(self, dimension: int | None = None):
            self.dimension = dimension

        def get_col_spec(self, **_kw):
            return "VECTOR"

    sqlalchemy_mod.Vector = Vector
    pgvector_mod.sqlalchemy = sqlalchemy_mod
    sys.modules["pgvector"] = pgvector_mod
    sys.modules["pgvector.sqlalchemy"] = sqlalchemy_mod

from backend.services import recommendation_runtime


def test_build_snapshot_id_is_deterministic() -> None:
    snapshot = {
        "domain": "백엔드",
        "inputFilters": {"clientEngine": "", "gameGenre": "", "devLanguage": ""},
        "evidenceCount": 10,
        "feedbackCount": 3,
        "topCategories": ["실전 운용"],
        "topTech": ["FastAPI"],
        "selectedModels": ["Gemini Flash"],
        "selectedWorkflow": ["수집 → 분류 → 요약"],
    }

    first = recommendation_runtime.build_snapshot_id(snapshot)
    second = recommendation_runtime.build_snapshot_id(snapshot)

    assert first == second
    assert len(first) == 16


def test_upsert_snapshot_persists_data(tmp_path, monkeypatch) -> None:
    snapshot_file = tmp_path / "recommendation_snapshots.json"
    monkeypatch.setattr(recommendation_runtime, "_SNAPSHOT_PATH", snapshot_file)

    snapshot = {
        "domain": "백엔드",
        "inputFilters": {"clientEngine": "", "gameGenre": "", "devLanguage": ""},
        "evidenceCount": 1,
        "feedbackCount": 0,
        "topCategories": [],
        "topTech": [],
        "selectedModels": [],
        "selectedWorkflow": [],
    }
    snapshot_id = recommendation_runtime.build_snapshot_id(snapshot)

    recommendation_runtime.upsert_snapshot(snapshot_id, snapshot)
    store = recommendation_runtime.load_snapshot_store()

    assert snapshot_id in store
    assert store[snapshot_id]["snapshotId"] == snapshot_id
    assert store[snapshot_id]["domain"] == "백엔드"
