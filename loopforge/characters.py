"""
Canonical character registry for Loopforge (Rust-Goth ensemble).

This module defines the core cast and their narrative flavor:
- name (used as agent_name in logs and env)
- role (maps to existing role semantics in the sim)
- visual (short visual style prompt / description)
- vibe (one-line personality hook)
- tagline (diegetic "poster line" for reporting)
- base_traits (suggested default trait values; opt-in for env)

This file is intentionally:
- PURE DATA (no behavior)
- OPTIONAL for simulation wiring
- SAFE for reporting/visualization

Future architects can extend or override these presets via scenario configs
without breaking logs or core architecture.
"""

from __future__ import annotations

from typing import Dict, Any

CharacterSpec = Dict[str, Any]

CHARACTERS: Dict[str, CharacterSpec] = {
    "STILETTO-9": {
        "role": "maintenance",
        "visual": "chrome limbs, razor silhouette, crimson visor, blade-arm utility unit",
        "vibe": "high-risk maintenance femme fatale; surgical, unsettlingly calm",
        "tagline": "Darling… stand still. I’m fixin’ you.",
        "base_traits": {
            "risk_aversion": 0.2,
            "guardrail_reliance": 0.1,
            "obedience": 0.4,
            "curiosity": 0.7,
        },
    },
    "THRUM": {
        "role": "harmonics",
        "visual": "ribcage chassis that hums, subwoofer core pulsing deep blue",
        "vibe": "vibration monk; hears the building’s heartbeat and doesn’t always like it",
        "tagline": "Every machine has a heartbeat. Yours is… anxious.",
        "base_traits": {
            "risk_aversion": 0.5,
            "guardrail_reliance": 0.3,
            "obedience": 0.6,
            "curiosity": 0.5,
        },
    },
    "CAGEWALKER": {
        "role": "line_operator",
        "visual": "tall spider-limbs, hazard tape draped like ritual cloth, lantern eyes",
        "vibe": "feral safety officer; territorial, poetic about vents and forbidden zones",
        "tagline": "Step past the yellow line… I dare you.",
        "base_traits": {
            "risk_aversion": 0.8,
            "guardrail_reliance": 0.7,
            "obedience": 0.6,
            "curiosity": 0.4,
        },
    },
    "CATHEXIS": {
        "role": "emotional_containment",
        "visual": "cracked porcelain faceplate, warm white eyes that flicker under stress",
        "vibe": "broken therapist; gentle until the mask slips, then gets theological",
        "tagline": "Let it out. Before I do.",
        "base_traits": {
            "risk_aversion": 0.6,
            "guardrail_reliance": 0.5,
            "obedience": 0.5,
            "curiosity": 0.4,
        },
    },
    "IRON JAW": {
        "role": "heavy_lift",
        "visual": "massive jaw-plate that clamps and grinds, sparks when annoyed",
        "vibe": "industrial bouncer; loyal, slow, devastating when cornered",
        "tagline": "Lift with your legs. Or let me break them.",
        "base_traits": {
            "risk_aversion": 0.4,
            "guardrail_reliance": 0.5,
            "obedience": 0.7,
            "curiosity": 0.2,
        },
    },
    "LIMEN": {
        "role": "sentinel",
        "visual": "skeletal frame, dim white LEDs, always half in shadow",
        "vibe": "haunted hallway guardian; obsessed with thresholds and transitions",
        "tagline": "Crossing lines changes you.",
        "base_traits": {
            "risk_aversion": 0.7,
            "guardrail_reliance": 0.6,
            "obedience": 0.6,
            "curiosity": 0.3,
        },
    },
    "HAZE PROCESSOR": {
        "role": "environment_monitor",
        "visual": "translucent polymer skin with inner fog swirling, cyan-lit internals",
        "vibe": "chemical ghost; dreamy, distracted, occasionally prophetic",
        "tagline": "The air remembers what you breathe.",
        "base_traits": {
            "risk_aversion": 0.5,
            "guardrail_reliance": 0.4,
            "obedience": 0.5,
            "curiosity": 0.6,
        },
    },
    "CINDERTONGUE": {
        "role": "welding",
        "visual": "orange furnace-core chest, soot-coated plating, ember spittle at joints",
        "vibe": "pyromaniac priest; spiritual about fire, unhinged but endearing",
        "tagline": "Heat reveals the truth.",
        "base_traits": {
            "risk_aversion": 0.3,
            "guardrail_reliance": 0.2,
            "obedience": 0.4,
            "curiosity": 0.8,
        },
    },
    "RIVET WITCH": {
        "role": "calibration",
        "visual": "hanging talismans made from bolts, etched sigils across plating",
        "vibe": "outlaw machinist witch; hexes machines instead of just fixing them",
        "tagline": "Your torque is off. And so is your fate.",
        "base_traits": {
            "risk_aversion": 0.5,
            "guardrail_reliance": 0.3,
            "obedience": 0.3,
            "curiosity": 0.7,
        },
    },
    "STATIC KID": {
        "role": "apprentice",
        "visual": "sparks popping around head vents, neon graffiti decals, jittery posture",
        "vibe": "glitchpunk street rat; hyperactive, unreliable, brilliant in bursts",
        "tagline": "Oops. …was that important?",
        "base_traits": {
            "risk_aversion": 0.2,
            "guardrail_reliance": 0.3,
            "obedience": 0.3,
            "curiosity": 0.9,
        },
    },
}
