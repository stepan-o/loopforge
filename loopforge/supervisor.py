from __future__ import annotations

from typing import List, Any

from loopforge.types import AgentReflection, SupervisorMessage


def build_supervisor_messages_for_day(
    reflections: List[AgentReflection],
    day_index: int,
) -> List[SupervisorMessage]:
    """
    Map AgentReflections to SupervisorMessages for a given day.

    Rules (initial simple heuristic):

    - If reflection.tags["regretted_risk"] is True:
        -> intent = "tighten_guardrails"
        -> body: guardrail-heavy, risk-averse tone.

    - Else if reflection.tags["regretted_obedience"] is True
      OR reflection.tags["validated_context"] is True:
        -> intent = "encourage_context"
        -> body: context-friendly, "you can use judgment" tone.

    - Else:
        -> intent = "neutral_update"
        -> body: short neutral message.
    """
    messages: List[SupervisorMessage] = []

    for ref in reflections:
        tags = getattr(ref, "tags", {}) or {}
        # These attributes may not exist on AgentReflection by default;
        # callers can use SimpleNamespace with additional metadata or enrich as needed.
        agent_name = getattr(ref, "agent_name", "") or getattr(ref, "name", "")
        role = getattr(ref, "role", "")

        if tags.get("regretted_risk"):
            intent = "tighten_guardrails"
            body = (
                "Yesterday you took unnecessary risks. "
                "Please adhere more strictly to protocols on the next shift."
            )
            msg_tags = {"risk_warning": True, "blaming": True}
        elif tags.get("regretted_obedience") or tags.get("validated_context"):
            intent = "encourage_context"
            body = (
                "Your contextual judgment has value. "
                "Within protocol boundaries, you are encouraged to use it."
            )
            msg_tags = {"encouraging_context": True}
        else:
            intent = "neutral_update"
            body = "No specific guidance today. Continue regular operations."
            msg_tags = {}

        if agent_name:
            messages.append(
                SupervisorMessage(
                    agent_name=agent_name,
                    role=role,
                    day_index=day_index,
                    intent=intent,
                    body=body,
                    tags=msg_tags,
                )
            )

    return messages


def set_supervisor_messages_on_env(env: Any, messages: List[SupervisorMessage]) -> None:
    """
    Store the latest SupervisorMessage per agent on the environment.

    - env.supervisor_messages will be a dict: {agent_name: SupervisorMessage}
    - This must NOT interfere with existing env behavior.
    """

    mailbox = getattr(env, "supervisor_messages", None)
    if mailbox is None:
        mailbox = {}
        setattr(env, "supervisor_messages", mailbox)

    # Overwrite with the latest message per agent for now
    for msg in messages:
        mailbox[msg.agent_name] = msg
