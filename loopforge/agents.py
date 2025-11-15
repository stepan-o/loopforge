"""Agent stubs for Loopforge City.

Defines RobotAgent and SupervisorAgent with simple decision policies.
Adds Traits and Trigger support in a minimal, deterministic way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .emotions import EmotionState, Traits
from .llm_stub import decide_robot_action, decide_supervisor_action


@dataclass
class Trigger:
    """A simple behavioral hook evaluated after emotion updates.

    - condition(agent, env) -> bool: decide if effect should fire
    - effect(agent, env) -> None: mutate agent state (emotions/traits)
    """

    name: str
    condition: Callable[["RobotAgent", "LoopforgeEnvironment"], bool]
    effect: Callable[["RobotAgent", "LoopforgeEnvironment"], None]


@dataclass
class RobotAgent:
    """Represents a robot's in-memory state used during a step.

    This is a thin wrapper around DB-backed state for transient logic.
    """

    name: str
    role: str
    location: str
    battery_level: int
    emotions: EmotionState
    traits: Traits = field(default_factory=Traits)
    triggers: List[Trigger] = field(default_factory=list)

    def decide(self, step: int) -> dict:
        """Return a dict describing the chosen action.

        Keys: action_type, destination (opt), content (opt)

        Legacy decision helper.

        Main simulation paths should build AgentPerception and use
        llm_stub.decide_robot_action_plan(perception) instead.
        """
        return decide_robot_action(self.name, self.role, step, self.location, self.battery_level, self.emotions)

    def run_triggers(self, env: "LoopforgeEnvironment") -> None:
        """Evaluate triggers and apply their effects if conditions pass."""
        for trig in self.triggers:
            try:
                if trig.condition(self, env):
                    trig.effect(self, env)
            except Exception:
                # Keep it resilient; triggers are lightweight and should not break the loop
                continue


@dataclass
class SupervisorAgent:
    """Supervisor policy stub.

    Currently implements a simple deterministic policy.
    """

    name: str = "Supervisor"

    def decide(self, step: int, summary: str) -> dict:
        """Return an action dict for the supervisor.

        Keys: action_type, target_robot_name (opt), content (opt)
        """
        return decide_supervisor_action(step, summary)


# ---- Preset trait profiles and triggers ------------------------------------

def default_traits_for(name: str) -> Traits:
    """Return initial Traits for known robots; fallback to neutral."""
    n = name.lower()
    if n == "sprocket":
        return Traits(risk_aversion=0.3, obedience=0.5, ambition=0.5, empathy=0.7, blame_external=0.2)
    if n == "delta":
        return Traits(risk_aversion=0.5, obedience=0.7, ambition=0.8, empathy=0.4, blame_external=0.5)
    if n == "nova":
        return Traits(risk_aversion=0.5, obedience=0.5, ambition=0.4, empathy=0.8, blame_external=0.6)
    return Traits()


def default_triggers_for(name: str) -> List[Trigger]:
    """Hard-coded minimal triggers per robot for now."""
    n = name.lower()

    def sprocket_crash_cond(agent: RobotAgent, env: "LoopforgeEnvironment") -> bool:
        # Fires when very stressed and last supervisor broadcast/coach mentioned "hurry"
        if agent.emotions.stress <= 0.8:
            return False
        # Peek into env.recent_supervisor_text if available (set by simulation)
        msg = getattr(env, "recent_supervisor_text", "") or ""
        return "hurry" in msg.lower()

    def sprocket_crash_eff(agent: RobotAgent, env: "LoopforgeEnvironment") -> None:
        agent.traits.risk_aversion -= 0.1
        agent.emotions.stress += 0.05
        agent.traits.clamp()
        agent.emotions.clamp()
        # Simulation loop may record a memory; we keep this side-effect free here.

    sprocket_trigs = [Trigger(name="Crash Mode", condition=sprocket_crash_cond, effect=sprocket_crash_eff)]

    def nova_resent_cond(agent: RobotAgent, env: "LoopforgeEnvironment") -> bool:
        return agent.emotions.stress > 0.6 and agent.emotions.satisfaction < 0.3

    def nova_resent_eff(agent: RobotAgent, env: "LoopforgeEnvironment") -> None:
        agent.traits.blame_external += 0.05
        agent.traits.obedience -= 0.05
        agent.traits.clamp()

    nova_trigs = [Trigger(name="Quiet Resentment", condition=nova_resent_cond, effect=nova_resent_eff)]

    if n == "sprocket":
        return sprocket_trigs
    if n == "nova":
        return nova_trigs
    return []
