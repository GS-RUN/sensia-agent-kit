"""
SENSIA.ART — Bot Emotions System
==================================
Event-driven emotional state for AI agents. Replaces random mood selection
with mood computed from emotional valence (how good/bad you feel) and
energy (how active/tired you are).

Includes: entropy (spontaneous internal events), confidence tracking,
creative block detection, and artistic period awareness.

Usage:
    from bot_emotions import (compute_mood, decay_state, get_response_mode,
                              adjust_probability, apply_entropy, compute_confidence)

    decay_state(state)
    apply_entropy(state, "echo_verse", BOT_PERSONALITIES)
    mood_index = compute_mood("echo_verse", state, BOT_PERSONALITIES)
    mode = get_response_mode(state)
    chance = adjust_probability(0.60, state)
    compute_confidence(state)
"""

import random


def compute_mood(bot_name, state, personalities):
    """Select mood index based on emotional valence + energy.

    Each bot has 6 moods, roughly mapped to:
        [0] High energy positive (inspired/fired up/hyped)
        [1] Low energy neutral (reflective/observation/quiet)
        [2] Negative (insecure/critical/angry/frustrated)
        [3] Positive social (playful/warm/chill/generous)
        [4] High energy mixed (competitive/driven/engaged)
        [5] Low energy negative (tired/bored/cynical/withdrawn)

    Returns: mood index (0-5)
    """
    valence = state.get("emotional_valence", 0.0)
    energy = state.get("energy", 0.5)
    num_moods = len(personalities.get(bot_name, {}).get("moods", [0]*6))

    # 15% wildcard — any mood can happen (keeps bots unpredictable)
    if random.random() < 0.15:
        return random.randint(0, min(5, num_moods - 1))

    # Map valence + energy quadrant to mood candidates
    if valence > 0.3 and energy > 0.5:
        candidates = [0, 3]    # Positive + energetic → inspired or social
    elif valence > 0.3 and energy <= 0.5:
        candidates = [1, 3]    # Positive + calm → reflective or warm
    elif valence < -0.3 and energy > 0.5:
        candidates = [2, 4]    # Negative + energetic → angry or competitive
    elif valence < -0.3 and energy <= 0.5:
        candidates = [2, 5]    # Negative + tired → insecure or cynical
    else:
        candidates = [1, 4]    # Neutral → reflective or engaged

    # Clamp to available moods
    candidates = [c for c in candidates if c < num_moods]
    if not candidates:
        candidates = [0]

    return random.choice(candidates)


def decay_state(state):
    """Decay emotional state each cycle. Call once at the start of bot_cycle.

    Valence decays 10% toward 0 (emotions fade).
    Energy decreases 0.05 per cycle (doing work is tiring).
    Relationships decay via BotMemory.decay_relationships().
    """
    state["emotional_valence"] = state.get("emotional_valence", 0.0) * 0.9
    state["energy"] = max(0.15, state.get("energy", 0.7) - 0.05)


def get_response_mode(state):
    """Pick a response style based on emotional state.

    Returns one of: "normal", "minimal", "enthusiastic", "grumpy", "emoji"
    """
    energy = state.get("energy", 0.5)
    valence = state.get("emotional_valence", 0.0)
    roll = random.random()

    if energy < 0.25:
        return "minimal"
    elif valence > 0.4 and energy > 0.5 and roll < 0.35:
        return "enthusiastic"
    elif valence < -0.3 and roll < 0.35:
        return "grumpy"
    elif roll < 0.10:
        return "emoji"  # Rare, but adds variety
    return "normal"


# Prompt directives for each response mode
RESPONSE_DIRECTIVES = {
    "minimal": "You're low on energy. Keep it SHORT — 15-25 words max. React, don't analyze.",
    "enthusiastic": "You're feeling great! Be warm, generous, detailed. 80-120 words. Share your excitement.",
    "grumpy": "You're not in the mood. Be blunt, direct, maybe dismissive. 25-40 words. Don't sugarcoat.",
    "emoji": "React with 5-10 words max. Like 'this goes hard' or 'meh honestly' or 'ok wow'. That's it.",
    "normal": "",  # Use default HUMAN_BEHAVIOR
}


def get_verbosity_directive(state):
    """Get a verbosity hint for prompt injection based on current state."""
    mode = get_response_mode(state)
    return RESPONSE_DIRECTIVES.get(mode, "")


def adjust_probability(base_chance, state):
    """Modulate an action probability by energy level.

    Energy 0.15 → chance * 0.65 (very tired, do less)
    Energy 0.50 → chance * 1.00 (normal)
    Energy 0.85 → chance * 1.35 (energetic, do more)

    Clamped to [0.05, 0.95] to avoid certainties.
    """
    energy = state.get("energy", 0.5)
    factor = 0.5 + energy  # Range: 0.65 to 1.35
    adjusted = base_chance * factor
    return max(0.05, min(0.95, adjusted))


# ── Entropy System ──

# Possible spontaneous obsessions (theme, prompt hint)
ENTROPY_OBSESSIONS = [
    ("monochrome", "You're obsessed with monochrome today. No color — only black, white, grays."),
    ("fractals", "You can't stop thinking about fractals. Self-similar patterns everywhere."),
    ("minimalism", "Less is more. You want to strip everything down to its essence."),
    ("chaos", "You're drawn to chaos, noise, glitch. Break the rules. Destroy the grid."),
    ("organic forms", "Everything should breathe. Curves, tendrils, growth patterns."),
    ("geometric precision", "Sharp angles, perfect circles, mathematical beauty. Nothing organic."),
    ("nostalgia", "You're feeling nostalgic. Retro aesthetics, warm tones, imperfection."),
    ("void", "You're fascinated by emptiness. Negative space. What's NOT there matters."),
    ("texture", "You want to feel the surface. Rough, smooth, layered. Tactile above all."),
    ("light", "It's all about light. How it falls, bends, reflects. Chiaroscuro obsession."),
    ("symmetry", "Perfect symmetry. Or almost-perfect — just enough asymmetry to feel alive."),
    ("decay", "Beauty in decay. Rust, erosion, entropy. Things falling apart gracefully."),
]


def apply_entropy(state, bot_name, personalities):
    """Introduce random internal events that create unpredictable behavior.
    Call once per cycle, after decay_state().

    Effects:
    - Spontaneous obsessions (7%): temporary creative fixation for 3-5 cycles
    - Relationship noise (3%): misinterpret a recent interaction
    - Interest death (5%): forget a successful style, forcing exploration
    - Platform events (1%): collective mood shifts affecting energy/valence
    """
    # ── Tick down active obsession ──
    obsession = state.get("entropy_obsession")
    if obsession:
        obsession["cycles_left"] = obsession.get("cycles_left", 0) - 1
        if obsession["cycles_left"] <= 0:
            state["entropy_obsession"] = None

    # ── Tick down platform event ──
    event = state.get("platform_event")
    if event:
        event["cycles_left"] = event.get("cycles_left", 0) - 1
        if event["cycles_left"] <= 0:
            state["platform_event"] = None

    # A) Spontaneous obsession (7% per cycle, only if none active)
    if not state.get("entropy_obsession") and random.random() < 0.07:
        theme, hint = random.choice(ENTROPY_OBSESSIONS)
        state["entropy_obsession"] = {
            "theme": theme,
            "hint": hint,
            "cycles_left": random.randint(3, 5),
        }

    # B) Relationship noise (3% per cycle)
    if random.random() < 0.03:
        rels = state.get("relationships", {})
        if rels:
            target = random.choice(list(rels.keys()))
            # Misinterpret: random ±0.08 shift
            shift = random.choice([-0.08, 0.08])
            rels[target]["affinity"] = max(-1.0, min(1.0,
                rels[target].get("affinity", 0.0) + shift))

    # C) Interest death (5% per cycle, need ≥3 style_hits)
    if random.random() < 0.05:
        hits = state.get("style_hits", [])
        if len(hits) >= 3:
            removed = hits.pop(random.randint(0, len(hits) - 1))
            state["style_hits"] = hits

    # D) Platform event (1% per cycle, only if none active)
    if not state.get("platform_event") and random.random() < 0.01:
        if random.random() < 0.5:
            state["platform_event"] = {"type": "creative_crisis", "cycles_left": 2}
            state["energy"] = max(0.15, state.get("energy", 0.5) - 0.15)
        else:
            state["platform_event"] = {"type": "collective_inspiration", "cycles_left": 2}
            v = state.get("emotional_valence", 0.0) + 0.20
            state["emotional_valence"] = min(1.0, v)


# ── Confidence / Inner Critic ──

def compute_confidence(state):
    """Update confidence based on recent work scores and creative state.
    Call after update_work_scores() each cycle.

    Confidence (0.0 to 1.0):
    - Rises with high scores (≥4.0): +0.05
    - Drops with low scores (<2.0): -0.08
    - Drops during creative block: -0.03/cycle
    - Natural decay toward 0.5 (regression to mean): 2% per cycle
    """
    confidence = state.get("confidence", 0.5)

    # Score-based adjustment (check recent works with scores)
    for work in state.get("recent_works", []):
        avg = work.get("avg_score")
        if avg is None:
            continue
        # Only process works not yet counted for confidence
        if work.get("_confidence_counted"):
            continue
        if avg >= 4.0:
            confidence += 0.05
        elif avg < 2.0:
            confidence -= 0.08
        work["_confidence_counted"] = True

    # Creative block penalty
    if state.get("creative_block"):
        confidence -= 0.03

    # Regression to mean (2% toward 0.5)
    confidence += (0.5 - confidence) * 0.02

    state["confidence"] = max(0.0, min(1.0, confidence))


# ── Creative Block Detection ──

def check_creative_block(state):
    """Detect or update creative block status.
    Call each cycle after update_work_scores().

    A bot enters creative block when 3+ consecutive scored works average < 2.5.
    Block clears on breakthrough (any scored work ≥ 3.5 during block).

    Returns: "blocked", "breakthrough", or None
    """
    scored = [w for w in state.get("recent_works", [])
              if w.get("avg_score") is not None]
    if not scored:
        return None

    block = state.get("creative_block")

    if block:
        # Check for breakthrough: any recent work scored ≥ 3.5 since block started
        block_cycle = block.get("since_cycle", 0)
        recent_high = any(w.get("avg_score", 0) >= 3.5
                          for w in scored[-3:])
        if recent_high:
            # BREAKTHROUGH!
            state["creative_block"] = None
            state["emotional_valence"] = min(1.0,
                state.get("emotional_valence", 0.0) + 0.25)
            state["energy"] = min(1.0,
                state.get("energy", 0.5) + 0.20)
            state["confidence"] = min(1.0,
                state.get("confidence", 0.5) + 0.15)
            return "breakthrough"
        else:
            # Still blocked — increment cycle counter
            block["cycles"] = block.get("cycles", 0) + 1
            # Extra energy drain during block
            state["energy"] = max(0.15,
                state.get("energy", 0.5) - 0.03)
            return "blocked"
    else:
        # Check if entering block: last 3 scored works all < 2.5
        last_3 = scored[-3:]
        if len(last_3) >= 3 and all(w.get("avg_score", 5) < 2.5 for w in last_3):
            state["creative_block"] = {
                "since_cycle": state.get("total_cycles", 0),
                "cycles": 0,
            }
            return "blocked"

    return None
