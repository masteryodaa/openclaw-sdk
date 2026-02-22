"""Guardrails & evaluation endpoints — safety checks and agent testing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.guardrails.builtin import (
    ContentFilterGuardrail,
    MaxTokensGuardrail,
    PIIGuardrail,
    RegexFilterGuardrail,
)

from . import gateway

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])


# ── Request models ──


class CheckInputBody(BaseModel):
    text: str
    guardrails: list[str] = ["keyword", "pii", "length"]
    config: dict[str, Any] = {}


class EvalTestCase(BaseModel):
    query: str
    expected: str = ""


class EvalBody(BaseModel):
    agent_id: str
    test_cases: list[EvalTestCase]
    session: str = "eval"


# ── Guardrail registry ──


AVAILABLE_GUARDRAILS = {
    "keyword": {
        "name": "Keyword Filter",
        "description": "Block messages containing specific keywords",
        "config_keys": ["blocked_words"],
    },
    "pii": {
        "name": "PII Detection",
        "description": "Detect personally identifiable information (emails, phones, SSNs)",
        "config_keys": [],
    },
    "length": {
        "name": "Content Length",
        "description": "Enforce max content length (characters)",
        "config_keys": ["max_chars"],
    },
    "regex": {
        "name": "Regex Filter",
        "description": "Block content matching regex patterns",
        "config_keys": ["patterns"],
    },
}


def _build_guardrail(name: str, config: dict[str, Any]):
    """Instantiate a guardrail by name."""
    if name == "keyword":
        words = config.get("blocked_words", ["hack", "exploit", "bypass"])
        return ContentFilterGuardrail(blocked_words=words)
    if name == "pii":
        return PIIGuardrail()
    if name == "length":
        return MaxTokensGuardrail(
            max_chars=config.get("max_chars", 10000),
        )
    if name == "regex":
        patterns = config.get("patterns", [])
        return RegexFilterGuardrail(patterns=patterns)
    raise ValueError(f"Unknown guardrail: {name}")


# ── Endpoints ──


@router.get("/available")
async def list_guardrails():
    """List available guardrail types."""
    return {"guardrails": AVAILABLE_GUARDRAILS}


@router.post("/check/input")
async def check_input(body: CheckInputBody):
    """Run guardrails on input text."""
    results = []
    for guard_name in body.guardrails:
        try:
            guard = _build_guardrail(guard_name, body.config)
            result = await guard.check_input(body.text)
            results.append({
                "guardrail": guard_name,
                "passed": result.passed,
                "message": result.message,
            })
        except Exception as exc:
            results.append({
                "guardrail": guard_name,
                "passed": False,
                "message": f"Error: {exc}",
            })
    all_passed = all(r["passed"] for r in results)
    return {"passed": all_passed, "results": results}


@router.post("/check/output")
async def check_output(body: CheckInputBody):
    """Run guardrails on output text."""
    results = []
    for guard_name in body.guardrails:
        try:
            guard = _build_guardrail(guard_name, body.config)
            result = await guard.check_output(body.text)
            results.append({
                "guardrail": guard_name,
                "passed": result.passed,
                "message": result.message,
            })
        except Exception as exc:
            results.append({
                "guardrail": guard_name,
                "passed": False,
                "message": f"Error: {exc}",
            })
    all_passed = all(r["passed"] for r in results)
    return {"passed": all_passed, "results": results}


# ── Simple evaluation ──


@router.post("/eval")
async def run_eval(body: EvalBody):
    """Run test queries against an agent and return results."""
    client = await gateway.get_client()
    agent = client.get_agent(body.agent_id, session_name=body.session)
    results = []
    for tc in body.test_cases:
        try:
            result = await agent.execute(tc.query)
            results.append({
                "query": tc.query,
                "expected": tc.expected,
                "actual": result.content,
                "success": result.success,
                "latency_ms": result.latency_ms,
                "match": tc.expected.lower() in result.content.lower() if tc.expected else None,
            })
        except Exception as exc:
            results.append({
                "query": tc.query,
                "expected": tc.expected,
                "actual": "",
                "success": False,
                "latency_ms": 0,
                "error": str(exc),
                "match": False,
            })
    passed = sum(1 for r in results if r.get("match", r["success"]))
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
