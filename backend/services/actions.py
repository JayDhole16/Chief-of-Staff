"""Server-side action proposal construction; this module never performs external writes."""

import hashlib
from dataclasses import dataclass
from typing import Literal

from backend.policy.engine import PolicyDecision, PolicyInput, evaluate_policy


@dataclass(frozen=True)
class ServerRenderedAction:
    """Action fields assembled by trusted server code, not accepted from an agent payload."""

    action_ref: str
    recipient_email: str
    subject: str
    rendered_body: str
    policy_input: PolicyInput


@dataclass(frozen=True)
class ProposedAction:
    action_ref: str
    recipient_email: str
    subject: str
    rendered_body: str
    rendered_hash: str
    policy_decision: PolicyDecision
    status: Literal["ready", "pending_approval", "blocked"]


def propose_action(action: ServerRenderedAction) -> ProposedAction:
    """Hash the server-rendered content and classify it without executing it."""
    if not action.action_ref.strip():
        raise ValueError("action_ref must be non-empty")
    if "@" not in action.recipient_email:
        raise ValueError("recipient_email must be a verified email address")
    if not action.subject.strip() or not action.rendered_body.strip():
        raise ValueError("subject and rendered_body must be non-empty")
    decision = evaluate_policy(action.policy_input)
    if decision.verdict == "BLOCK":
        status: Literal["ready", "pending_approval", "blocked"] = "blocked"
    elif decision.verdict == "ASK":
        status = "pending_approval"
    else:
        status = "ready"
    return ProposedAction(
        action_ref=action.action_ref,
        recipient_email=action.recipient_email,
        subject=action.subject,
        rendered_body=action.rendered_body,
        rendered_hash=hashlib.sha256(action.rendered_body.encode("utf-8")).hexdigest(),
        policy_decision=decision,
        status=status,
    )
