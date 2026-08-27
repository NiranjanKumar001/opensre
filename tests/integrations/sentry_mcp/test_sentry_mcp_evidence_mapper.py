"""Tests for Sentry MCP evidence mappers."""

from __future__ import annotations

from typing import Any

from integrations.sentry_mcp.tools.sentry_mcp_tool import (
    _map_call_sentry_tool,
    _map_list_sentry_tools,
)
from tools.investigation.stages.gather_evidence.tools import merge_tool_evidence
from tools.registry import get_registered_tool


def test_sentry_tools_carried_by_registry() -> None:
    """Ensure sentry_mcp tools carry evidence mappers in the registry."""
    call_tool = get_registered_tool("call_sentry_tool")
    assert call_tool is not None
    assert call_tool.evidence_mapper is not None

    list_tool = get_registered_tool("list_sentry_tools")
    assert list_tool is not None
    assert list_tool.evidence_mapper is not None


def test_map_call_sentry_tool_with_text() -> None:
    """Test recording evidence from text output."""
    evidence: dict[str, Any] = {}
    output: dict[str, Any] = {
        "available": True,
        "tool": "get_issue_details",
        "text": "Unhandled TypeError: Cannot read property 'id' of undefined",
    }
    _map_call_sentry_tool(evidence, output, {"tool_name": "get_issue_details"})

    entries = evidence.get("catalog_entries", [])
    assert len(entries) == 1
    assert entries[0]["source"] == "call_sentry_tool:get_issue_details"
    assert entries[0]["label"] == "Sentry MCP: get_issue_details"
    assert "Unhandled TypeError" in entries[0]["summary"]


def test_map_call_sentry_tool_with_structured_content() -> None:
    """Test recording evidence from structured content."""
    evidence: dict[str, Any] = {}
    output: dict[str, Any] = {
        "available": True,
        "tool": "search_issues",
        "structured_content": {"issue_id": "12345", "count": 42},
    }
    _map_call_sentry_tool(evidence, output, {"tool_name": "search_issues"})

    entries = evidence.get("catalog_entries", [])
    assert len(entries) == 1
    assert entries[0]["source"] == "call_sentry_tool:search_issues"
    assert entries[0]["label"] == "Sentry MCP: search_issues"


def test_map_call_sentry_tool_via_merge_tool_evidence_multiple_tools() -> None:
    """Test evidence pipeline integration preserves distinct Sentry MCP tool invocations."""
    evidence: dict[str, Any] = {}
    output_1: dict[str, Any] = {
        "available": True,
        "tool": "get_issue_details",
        "text": "Unhandled TypeError in main",
    }
    output_2: dict[str, Any] = {
        "available": True,
        "tool": "seer_analyze_issue",
        "text": "Root cause identified in commit abc1234",
    }
    merge_tool_evidence(evidence, "call_sentry_tool", output_1, {"tool_name": "get_issue_details"})
    merge_tool_evidence(evidence, "call_sentry_tool", output_2, {"tool_name": "seer_analyze_issue"})

    entries = evidence.get("catalog_entries", [])
    assert len(entries) == 2
    assert entries[0]["source"] == "call_sentry_tool:get_issue_details"
    assert entries[1]["source"] == "call_sentry_tool:seer_analyze_issue"


def test_map_call_sentry_tool_repeated_same_tool_no_collision() -> None:
    """Test that multiple calls to the exact same tool with different args do not collide."""
    evidence: dict[str, Any] = {}
    output_1: dict[str, Any] = {
        "available": True,
        "tool": "get_issue_details",
        "text": "Issue 101: TypeError in payment service",
    }
    output_2: dict[str, Any] = {
        "available": True,
        "tool": "get_issue_details",
        "text": "Issue 202: NullPointerException in auth service",
    }
    merge_tool_evidence(
        evidence,
        "call_sentry_tool",
        output_1,
        {"tool_name": "get_issue_details", "arguments": {"issue_id": "101"}},
    )
    merge_tool_evidence(
        evidence,
        "call_sentry_tool",
        output_2,
        {"tool_name": "get_issue_details", "arguments": {"issue_id": "202"}},
    )

    entries = evidence.get("catalog_entries", [])
    assert len(entries) == 2
    assert entries[0]["source"] == "call_sentry_tool:get_issue_details:101"
    assert entries[1]["source"] == "call_sentry_tool:get_issue_details:202"


def test_map_call_sentry_tool_ignores_empty_or_unavailable() -> None:
    """Test that unavailable, empty, or error outputs produce no evidence entries."""
    evidence: dict[str, Any] = {}

    # Unavailable / error output
    _map_call_sentry_tool(evidence, {"available": False, "error": "Not configured"}, {})
    assert "catalog_entries" not in evidence

    # Empty payload output
    _map_call_sentry_tool(evidence, {"available": True, "tool": "get_issue"}, {})
    assert "catalog_entries" not in evidence


def test_map_list_sentry_tools() -> None:
    """Test recording evidence from list_sentry_tools."""
    evidence: dict[str, Any] = {}
    output: dict[str, Any] = {
        "available": True,
        "tools": [{"name": "get_issue"}, {"name": "search_issues"}],
    }
    _map_list_sentry_tools(evidence, output, {})

    entries = evidence.get("catalog_entries", [])
    assert len(entries) == 1
    assert entries[0]["source"] == "list_sentry_tools"
    assert entries[0]["label"] == "Sentry MCP Tools"
    assert entries[0]["summary"] == "2 Sentry MCP tool(s) available"
