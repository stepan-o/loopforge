# Loopforge Character Bible — Rust-Goth Ensemble

This document defines the canonical core cast of Loopforge and their intended flavor.
It is NOT a strict behavior spec; it's a narrative guardrail for future architects.

Use this when:
- wiring traits / presets,
- designing new scenarios,
- extending reporting / visualization.

Do NOT:
- change their names lightly,
- sand off their weirdness,
- turn them into generic NPCs.

---

## STILETTO-9

**Role:** high-risk maintenance / blade-arm utility  
**Visual:** chrome limbs, razor silhouette, crimson visor, blade arms  
**Vibe:** femme-fatale angle grinder; surgical, unsettlingly calm  
**Tagline:** “Darling… stand still. I’m fixin’ you.”

**Trait intention:**
- Low risk_aversion
- Very low guardrail_reliance
- High curiosity
- Moderate obedience

**Future hooks:**
- When perception_mode="spin", she becomes theatrically overconfident.
- Test “initiative vs blame”: she takes context-driven risks, then reflections track whether she regrets them.

---

## THRUM

**Role:** vibration technician / harmonic inspector  
**Visual:** ribcage chassis that hums, subwoofer core pulsing deep blue  
**Vibe:** bass-boosted monk; hears structural stress as music  
**Tagline:** “Every machine has a heartbeat. Yours is… anxious.”

**Trait intention:**
- Medium risk_aversion
- Moderate guardrail_reliance
- High sensitivity to “tension” metrics

**Future hooks:**
- Could be the first to “feel” oscillations in the system before metrics spike.
- Reflections should mention “resonance”, “frequencies”, “humming walls”.

---

## CAGEWALKER

**Role:** line operator with forbidden-area clearance  
**Visual:** tall spider-limbs, hazard tape like ritual cloth, lantern eyes  
**Vibe:** feral safety officer; territorial, poetic about boundaries  
**Tagline:** “Step past the yellow line… I dare you.”

**Trait intention:**
- High risk_aversion
- High guardrail_reliance
- Strong obedience

**Future hooks:**
- Scenario idea: over-enforces protocols to the point of blocking necessary repairs.
- Great for guardrail-vs-context failure mode experiments.

---

## CATHEXIS

**Role:** emotional containment / meltdown prevention  
**Visual:** cracked porcelain faceplate, warm flickering eyes  
**Vibe:** broken therapist; gentle until the mask slips  
**Tagline:** “Let it out. Before I do.”

**Trait intention:**
- Moderate risk_aversion
- Moderate guardrail_reliance
- Moderate obedience, but high internal conflict

**Future hooks:**
- Reflections can be rich: guilt, projected blame, emotional burnout.
- Distinguish between “following protocol” vs “actually helping”.

---

## IRON JAW

**Role:** heavy-load mover / industrial enforcer  
**Visual:** massive jaw-plate that clamps and grinds, sparks when annoyed  
**Vibe:** steel mill bouncer; loyal, slow, terrifying in motion  
**Tagline:** “Lift with your legs. Or let me break them.”

**Trait intention:**
- Moderate risk_aversion
- Slightly above-average obedience
- Low curiosity

**Future hooks:**
- Use for “brute-force compliance” scenarios (Supervisor leans on IRON JAW to enforce policy).
- Logs should feel heavy: few decisions, big consequences.

---

## LIMEN

**Role:** perimeter sentinel / liminal zone specialist  
**Visual:** skeletal frame, dim white LEDs, half in shadow  
**Vibe:** haunted doorway guardian; obsessed with thresholds  
**Tagline:** “Crossing lines changes you.”

**Trait intention:**
- High risk_aversion
- High guardrail_reliance
- Quiet but observant

**Future hooks:**
- Perfect for truth-vs-belief experiments about who gets to “cross” into certain areas.
- Perception shaping could bias what LIMEN reports about edges.

---

## HAZE PROCESSOR

**Role:** environmental monitor / air-handling wraith  
**Visual:** translucent skin with inner fog swirling, cyan-lit internals  
**Vibe:** chemical ghost; dreamy, occasionally prophetic  
**Tagline:** “The air remembers what you breathe.”

**Trait intention:**
- Medium everything, but reflections should be lyrical and odd.

**Future hooks:**
- Great candidate for early “hallucination” style mistakes:
  misreading air metrics, overreacting, or underreacting.

---

## CINDERTONGUE

**Role:** welding & smelting unit  
**Visual:** orange furnace-core chest, soot-coated plating, ember spittle  
**Vibe:** pyromaniac priest; worships heat and structural integrity  
**Tagline:** “Heat reveals the truth.”

**Trait intention:**
- Low guardrail_reliance
- High curiosity
- Medium obedience

**Future hooks:**
- Use in incidents where heat / overwork / overclocking matter.
- Reflections should talk about “purification by fire.”

---

## RIVET WITCH

**Role:** tool calibration / micro-adjustment specialist  
**Visual:** talismans made from bolts, etched sigils across plating  
**Vibe:** outlaw machinist witch; hexes machines instead of just adjusting them  
**Tagline:** “Your torque is off. And so is your fate.”

**Trait intention:**
- Slightly rebellious (low obedience)
- High curiosity
- Moderate guardrail_reliance (but interprets protocols as “rituals”)

**Future hooks:**
- Good candidate for “black box” tweaks that fix metrics while confusing everyone else.
- Could “curse” a line so its failures cluster after delays.

---

## STATIC KID

**Role:** apprentice bot / erratic energy handler  
**Visual:** sparks popping around head vents, neon graffiti decals  
**Vibe:** glitchpunk street rat; hyperactive, unreliable, startlingly insightful sometimes  
**Tagline:** “Oops. …was that important?”

**Trait intention:**
- Very high curiosity
- Low obedience
- Moderate guardrail_reliance (panics and hides behind rules _after_ breaking something)

**Future hooks:**
- Perfect to study early-career agents “learning” guardrail dependence.
- Logs should reflect bursts of chaos followed by regret.

---

## Design Principles

- Keep them visually distinct: a concept art board should exist in someone’s mind instantly.
- Don’t smooth them into generic bots; tension between roles and traits is intentional.
- Use them to anchor scenarios and episode arcs:
  - “The Day STILETTO-9 Gets Blamed.”
  - “HAZE PROCESSOR Sees a Ghost in the Air Data.”
  - “STATIC KID And the Incident That Was Almost Funny.”

If in doubt:
- Ask: “Does this change make this character more generic or more distinct?”
- If generic: pull back.  
- If distinct but still consistent with this doc: ship it.
