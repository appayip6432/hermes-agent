"""Startup-only, profile-scoped alignment pin, including across compression/resume."""

from __future__ import annotations

import logging
import re

from agent.alignment_store import is_approved, load_snapshot
from agent.alignment_synthesis import RULES, render_prompt

logger = logging.getLogger(__name__)
_FRAME = re.compile(
    r"^<!-- hermes-alignment-v1 ([0-9a-f]{64}) ([a-z,]*) -->\n"
    r"([\s\S]{0,1800}?)\n<!-- /hermes-alignment-v1 -->$", re.MULTILINE,
)


def _frame(version, rules):
    return (f"<!-- hermes-alignment-v1 {version} {','.join(rules)} -->\n"
            f"{render_prompt(rules)}\n<!-- /hermes-alignment-v1 -->")


def _restore(prompt):
    """Recover only canonical catalog prose, without touching current config/artifacts."""
    matches = list(_FRAME.finditer(prompt))
    if len(matches) != 1:
        return ""
    match = matches[0]
    rules = match[2].split(",") if match[2] else []
    if rules != [rule for rule in RULES if rule in rules]:
        return ""
    canonical = _frame(match[1], rules)
    return canonical if match[0] == canonical else ""


def _startup(home):
    from hermes_cli.config import load_config_readonly
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    token = set_hermes_home_override(home)
    try:
        config = load_config_readonly().get("alignment_synthesis", {})
    finally:
        reset_hermes_home_override(token)
    if not isinstance(config, dict) or config.get("mode", "shadow") != "active":
        return ""
    version = config.get("version")
    store = home / "alignment"
    if not is_approved(store, version):
        logger.warning("Alignment synthesis omitted: selected version has not been reviewed")
        return ""
    snapshot = load_snapshot(store, version)
    return _frame(version, snapshot["rules"])


def frozen_alignment(agent):
    """Pin presence AND absence. Config changes only affect a new conversation.

    The owner-home helper respects multiplex scope before DB ownership. Persisted
    prompt bytes outrank live config, even for legacy sessions without this layer.
    """
    from agent.system_prompt import _agent_home, _session_prompt
    from hermes_constants import get_hermes_home

    pinned = getattr(agent, "_alignment_prompt_snapshot", None)
    if isinstance(pinned, str):
        return pinned
    stored = _session_prompt(agent, include_cached=not getattr(agent, "_alignment_session_reset", False))
    try:
        result = _restore(stored) if stored else _startup(_agent_home(agent) or get_hermes_home())
    except (OSError, ValueError, TypeError, KeyError):
        # Do not log evidence, paths or parser exception text: config and artifacts
        # can contain private material. Invalid input fails closed for this session.
        logger.warning("Alignment synthesis omitted: invalid or unreadable configuration/artifact")
        result = ""
    agent._alignment_prompt_snapshot = result
    return result


def reset_alignment(agent):
    """A reused agent must consult the destination session, not its old cached prompt."""
    agent._alignment_prompt_snapshot = None
    agent._alignment_session_reset = True
