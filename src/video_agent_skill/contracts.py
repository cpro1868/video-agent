from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Status = Literal["success", "error"]
Strategy = Literal["subtitle", "asr", "none"]


@dataclass(frozen=True)
class ResponseMeta:
    url: str
    strategy_used: Strategy
    language: str
    duration_seconds: int | None = None


@dataclass(frozen=True)
class ResponseContent:
    title: str
    summary: str
    key_points: list[str]
    detailed_content: list[dict[str, str]]
    tags: list[str]
    transcript_excerpt: str
    markdown: str = ""


@dataclass(frozen=True)
class ResponseError:
    code: str
    message: str


@dataclass(frozen=True)
class AgentResponse:
    status: Status
    meta: ResponseMeta
    content: ResponseContent | None
    error: ResponseError | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def success_response(meta: ResponseMeta, content: ResponseContent) -> AgentResponse:
    return AgentResponse(status="success", meta=meta, content=content, error=None)


def error_response(
    *,
    url: str,
    language: str,
    code: str,
    message: str,
    strategy_used: Strategy = "none",
) -> AgentResponse:
    return AgentResponse(
        status="error",
        meta=ResponseMeta(
            url=url,
            strategy_used=strategy_used,
            language=language,
            duration_seconds=None,
        ),
        content=None,
        error=ResponseError(code=code, message=message),
    )
