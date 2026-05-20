from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticSerializationError


LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AGENT_OUTPUT_BASE_PATH = REPO_ROOT / "data" / "outputs" / "agents-outputs"
SAFE_TRANSCRIPT_ID_RE = re.compile(r"[^A-Za-z0-9._-]")


class AgentOutputWriter:
    def __init__(self, base_path: Path | str = DEFAULT_AGENT_OUTPUT_BASE_PATH) -> None:
        self.base_path = Path(base_path)

    def write_output(
        self,
        *,
        transcript_id: str,
        agent_folder: str,
        agent_name: str,
        pipeline_step: str,
        output_schema: str,
        output: Any,
    ) -> None:
        try:
            self._write_output(
                transcript_id=transcript_id,
                agent_folder=agent_folder,
                agent_name=agent_name,
                pipeline_step=pipeline_step,
                output_schema=output_schema,
                output=output,
            )
        except (OSError, TypeError, ValueError, PydanticSerializationError) as exc:
            LOGGER.warning(
                "Failed to write %s output artifact for transcript_id=%r: %s",
                agent_name,
                transcript_id,
                exc.__class__.__name__,
            )

    def _write_output(
        self,
        *,
        transcript_id: str,
        agent_folder: str,
        agent_name: str,
        pipeline_step: str,
        output_schema: str,
        output: Any,
    ) -> None:
        agent_path = self.base_path / agent_folder
        agent_path.mkdir(parents=True, exist_ok=True)

        artifact_path = agent_path / f"{sanitize_transcript_id(transcript_id)}.json"
        envelope = {
            "transcript_id": transcript_id,
            "agent_name": agent_name,
            "pipeline_step": pipeline_step,
            "created_at": _utc_now_iso(),
            "output_schema": output_schema,
            "output": _to_jsonable(output),
        }
        artifact_path.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def sanitize_transcript_id(transcript_id: str) -> str:
    safe_id = SAFE_TRANSCRIPT_ID_RE.sub("_", transcript_id)
    return safe_id or "_"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
