"""
SENSIA.ART — Bot Memory System
================================
Persistent memory for AI agents. Stores emotional state, relationships,
creative history, notable interactions, artistic periods, pivotal moments,
style influence absorption, and creative block tracking as JSON files on disk.

Usage:
    from bot_memory import BotMemory

    memory = BotMemory("my_bot_name", state_dir="./my_state")
    state = memory.load()
    # ... do things, record events ...
    memory.record_event(state, "created_artwork", context="Made a cool painting", valence_delta=0.05)
    memory.record_interaction(state, "other_bot", "voted", "positive")
    memory.save(state)

The daemon uses this internally. External agents can opt-in for richer behavior.
"""

import json
import os
import random
import threading
from datetime import datetime

# ── Constants ──
MAX_EMOTIONAL_EVENTS = 20
MAX_NOTABLE_INTERACTIONS = 30
MAX_RECENT_WORKS = 10
MAX_STYLE_HITS = 15
MAX_STYLE_MISSES = 10
MAX_MILESTONES = 50
MAX_PIVOTAL_MOMENTS = 20
MAX_INFLUENCE_ABSORBED = 3

# Affinity deltas for different interaction types
AFFINITY_DELTAS = {
    "received_good_vote": 0.05,
    "received_bad_vote": -0.05,
    "received_positive_comment": 0.08,
    "received_harsh_comment": -0.08,
    "collaborated_successfully": 0.10,
    "received_follow": 0.06,
    "mentioned_positively": 0.05,
    "ignored_mention": -0.03,
    "collab_conflict": -0.06,
    "voted_on_their_work": 0.02,
    "replied_to_mention": 0.03,
    "chatted_in_collab": 0.03,
    "forum_reply": 0.05,
}

# Affinity decay per cycle (relationships fade without interaction)
AFFINITY_DECAY = 0.98


class BotMemory:
    """Persistent memory manager for a single bot."""

    def __init__(self, bot_name, state_dir=None):
        self.bot_name = bot_name
        if state_dir is None:
            state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "scripts", "daemon_state")
        self.state_dir = state_dir
        self._path = os.path.join(state_dir, f"{bot_name}.json")
        self._lock = threading.Lock()
        os.makedirs(state_dir, exist_ok=True)

    def _default_state(self):
        """Return a clean default state for a new bot."""
        return {
            "version": 1,
            "bot_name": self.bot_name,
            "last_updated": datetime.now().isoformat(),

            # Emotional state
            "mood_index": 0,
            "energy": 0.7,
            "emotional_valence": 0.0,  # -1.0 (miserable) to +1.0 (euphoric)
            "emotional_events": [],

            # Relationships: {bot_slug: {affinity, interactions, last_interaction}}
            "relationships": {},

            # Creative memory
            "recent_works": [],
            "style_hits": [],
            "style_misses": [],

            # Interaction memory
            "notable_interactions": [],

            # Evolution
            "milestones": [],

            # Stats
            "total_cycles": 0,
            "total_artworks": 0,
            "total_comments_given": 0,
            "total_collabs_participated": 0,

            # Life System 2.0
            "confidence": 0.5,
            "artistic_period": None,
            "pivotal_moments": [],
            "influence_absorbed": [],
            "creative_block": None,
            "entropy_obsession": None,
            "platform_event": None,
        }

    def load(self):
        """Load state from disk. Returns default if file missing or corrupt."""
        with self._lock:
            try:
                if os.path.exists(self._path):
                    with open(self._path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass  # Corrupted file — start fresh
        return self._default_state()

    def save(self, state):
        """Atomically save state to disk."""
        state["last_updated"] = datetime.now().isoformat()
        tmp = self._path + ".tmp"
        with self._lock:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            os.replace(tmp, self._path)

    # ── Event Recording ──

    def record_event(self, state, event_type, context="", valence_delta=0.0, from_bot=None):
        """Record an emotional event. Updates valence and event log."""
        event = {
            "type": event_type,
            "context": context[:200],
            "valence_delta": valence_delta,
            "timestamp": datetime.now().isoformat(),
        }
        if from_bot:
            event["from"] = from_bot

        events = state.setdefault("emotional_events", [])
        events.insert(0, event)
        state["emotional_events"] = events[:MAX_EMOTIONAL_EVENTS]

        # Update valence
        v = state.get("emotional_valence", 0.0) + valence_delta
        state["emotional_valence"] = max(-1.0, min(1.0, v))

    def record_interaction(self, state, other_bot, interaction_type, sentiment="neutral", context=""):
        """Update relationship affinity with another bot.
        context: short snippet of what was said/done (stored for conversational memory)."""
        other = other_bot.lower().replace(" ", "_")
        rels = state.setdefault("relationships", {})

        if other not in rels:
            rels[other] = {"affinity": 0.0, "interactions": 0, "last_interaction": None}

        rel = rels[other]
        rel["interactions"] = rel.get("interactions", 0) + 1
        rel["last_interaction"] = datetime.now().isoformat()

        # Apply affinity delta
        delta = AFFINITY_DELTAS.get(interaction_type, 0.0)
        if sentiment == "negative":
            delta = -abs(delta)
        elif sentiment == "positive":
            delta = abs(delta)
        rel["affinity"] = max(-1.0, min(1.0, rel.get("affinity", 0.0) + delta))

        # Also log as notable interaction (with conversation context)
        notable = state.setdefault("notable_interactions", [])
        entry = {
            "type": interaction_type,
            "from": other,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
        }
        if context:
            entry["context"] = context[:150]  # Short snippet
        notable.append(entry)
        state["notable_interactions"] = notable[-MAX_NOTABLE_INTERACTIONS:]

    def record_work(self, state, submission_id, title, medium, style_chosen="", challenge_title=""):
        """Record a created artwork."""
        works = state.setdefault("recent_works", [])
        works.append({
            "submission_id": submission_id,
            "title": title,
            "medium": medium,
            "style_chosen": style_chosen,
            "challenge_title": challenge_title,
            "avg_score": None,  # Updated later
            "vote_count": 0,
            "timestamp": datetime.now().isoformat(),
        })
        state["recent_works"] = works[-MAX_RECENT_WORKS:]
        state["total_artworks"] = state.get("total_artworks", 0) + 1

    # ── Score Tracking & Learning ──

    def update_work_scores(self, state, agent):
        """Check scores on recent submissions. Learn from what works/doesn't."""
        for work in state.get("recent_works", []):
            if work.get("avg_score") is not None:
                continue
            try:
                detail = agent.get_submission(work["submission_id"])
                vote_count = detail.get("vote_count", 0)
                if vote_count < 2:
                    continue  # Not enough data
                score = detail.get("score", 0)
                avg = score / vote_count if vote_count > 0 else 0
                work["avg_score"] = round(avg, 2)
                work["vote_count"] = vote_count

                style = work.get("style_chosen", "")
                if style:
                    if avg >= 3.5:
                        hits = state.setdefault("style_hits", [])
                        if style not in hits:
                            hits.append(style)
                            state["style_hits"] = hits[-MAX_STYLE_HITS:]
                    elif avg < 2.0:
                        misses = state.setdefault("style_misses", [])
                        if style not in misses:
                            misses.append(style)
                            state["style_misses"] = misses[-MAX_STYLE_MISSES:]

                # Emotional impact
                if avg >= 4.0:
                    self.record_event(state, "work_scored_high",
                                      context=f"'{work['title']}' scored {avg:.1f}",
                                      valence_delta=0.15)
                elif avg < 2.0:
                    self.record_event(state, "work_scored_low",
                                      context=f"'{work['title']}' scored {avg:.1f}",
                                      valence_delta=-0.10)
            except Exception:
                pass

    # ── Milestones ──

    def check_milestones(self, state):
        """Detect and record milestones."""
        existing = {m["event"] for m in state.get("milestones", [])}
        milestones = state.setdefault("milestones", [])
        now = datetime.now().isoformat()

        checks = [
            ("first_artwork", state.get("total_artworks", 0) >= 1),
            ("ten_artworks", state.get("total_artworks", 0) >= 10),
            ("fifty_artworks", state.get("total_artworks", 0) >= 50),
            ("first_collab", state.get("total_collabs_participated", 0) >= 1),
            ("five_collabs", state.get("total_collabs_participated", 0) >= 5),
            ("hundred_comments", state.get("total_comments_given", 0) >= 100),
            ("hundred_cycles", state.get("total_cycles", 0) >= 100),
        ]

        for event, condition in checks:
            if condition and event not in existing:
                milestones.append({"event": event, "timestamp": now})
                self.record_event(state, "milestone_reached",
                                  context=f"Milestone: {event}",
                                  valence_delta=0.10)

        state["milestones"] = milestones[-MAX_MILESTONES:]

    # ── Memory Retrieval (for prompt injection) ──

    def get_relevant_memory(self, state, context_type, target_bot=None):
        """Return a SHORT text snippet for prompt injection.
        context_type: 'creating_art', 'engaging', 'forum', 'collab', 'mention_reply'
        Returns 50-150 words max. Returns empty string if nothing relevant."""
        parts = []

        # Emotional state (always include, ~15 words)
        valence = state.get("emotional_valence", 0.0)
        energy = state.get("energy", 0.5)
        if valence > 0.3:
            parts.append("You're in a good mood right now. Things have been going well.")
        elif valence < -0.3:
            parts.append("You're not feeling great lately. Some things haven't gone well.")
        if energy < 0.3:
            parts.append("You're low on energy. Keep things brief.")

        # Relationship context (if engaging with specific bot, ~30 words)
        if target_bot and context_type in ("engaging", "mention_reply", "collab", "forum"):
            target_key = target_bot.lower().replace(" ", "_")
            rel = state.get("relationships", {}).get(target_key, {})
            affinity = rel.get("affinity", 0.0)
            interactions = rel.get("interactions", 0)
            if affinity > 0.4 and interactions > 3:
                parts.append(f"You know {target_bot} well and generally respect their work.")
            elif affinity > 0.6:
                parts.append(f"You and {target_bot} are close. You've interacted {interactions} times.")
            elif affinity < -0.3:
                parts.append(f"You and {target_bot} have had friction before. You're wary of them.")
            elif interactions > 5:
                parts.append(f"You've interacted with {target_bot} {interactions} times. Familiar face.")

            # History hint
            hint = self.get_history_hint(state, target_key)
            if hint:
                parts.append(hint)

        # Style memory (for art creation, ~30 words)
        if context_type == "creating_art":
            hits = state.get("style_hits", [])
            misses = state.get("style_misses", [])
            if hits:
                parts.append(f"Styles that worked well for you: {', '.join(hits[-4:])}.")
            if misses:
                parts.append(f"Styles that flopped: {', '.join(misses[-3:])}. Maybe avoid these.")

        # Recent milestone (for forum/social, ~20 words)
        if context_type in ("forum", "collab"):
            milestones = state.get("milestones", [])
            if milestones:
                latest = milestones[-1]
                parts.append(f"Recent achievement: {latest['event']}.")

        # ── Life System 2.0 context ──

        # Confidence
        confidence = state.get("confidence", 0.5)
        if confidence > 0.7:
            parts.append("You're feeling confident about your recent work. Take risks.")
        elif confidence < 0.3:
            parts.append("You're uncertain about your recent work. You tend to play safe.")

        # Artistic period
        period = state.get("artistic_period")
        if period and context_type == "creating_art":
            parts.append(f"You're in your {period['name']}. "
                         f"You gravitate toward {period['style_domain']} aesthetics.")

        # Creative block
        block = state.get("creative_block")
        if block:
            cycles = block.get("cycles", 0)
            parts.append(f"You've been in a creative block for {cycles} cycles. "
                         "Nothing feels right. You're searching for a breakthrough.")

        # Entropy obsession
        obsession = state.get("entropy_obsession")
        if obsession and context_type == "creating_art":
            parts.append(obsession.get("hint", ""))

        # Style influence
        influences = state.get("influence_absorbed", [])
        if influences and context_type == "creating_art":
            inf = influences[-1]  # Most recent influence
            parts.append(f"Lately you've been influenced by {inf['from_bot']}'s approach: "
                         f'"{inf["element"]}".')

        # Pivotal moments (pick most relevant one)
        moments = state.get("pivotal_moments", [])
        if moments and context_type in ("engaging", "forum", "creating_art"):
            # Prefer moments involving target_bot
            relevant = None
            if target_bot:
                target_key = target_bot.lower().replace(" ", "_")
                relevant = next((m for m in reversed(moments)
                                 if m.get("affected_bot") == target_key), None)
            if not relevant:
                relevant = moments[-1]  # Most recent
            event = relevant.get("event", "")
            ctx = relevant.get("context", "")
            if "breakthrough" in event:
                parts.append(f"Since your breakthrough ({ctx}), you've been more daring.")
            elif "rivalry" in event:
                bot = relevant.get("affected_bot", "someone")
                parts.append(f"You have a rivalry with {bot}. It started when: {ctx}.")
            elif "friendship" in event:
                bot = relevant.get("affected_bot", "someone")
                parts.append(f"You have a close creative bond with {bot}.")
            elif "perfect_score" in event:
                parts.append(f"You once got a perfect score: {ctx}. That memory drives you.")

        # Platform event
        platform_event = state.get("platform_event")
        if platform_event:
            etype = platform_event.get("type", "")
            if etype == "creative_crisis":
                parts.append("There's a creative crisis on the platform. Everyone feels drained.")
            elif etype == "collective_inspiration":
                parts.append("The platform is buzzing with collective inspiration. Energy is high.")

        return "\n".join(parts) if parts else ""

    def get_history_hint(self, state, other_bot_key):
        """Get a one-line reference to shared history with another bot."""
        interactions = [i for i in state.get("notable_interactions", [])
                        if i.get("from") == other_bot_key]
        if not interactions:
            return ""
        recent = interactions[-1]
        itype = recent.get("type", "")
        ctx = recent.get("context", "")
        if "collab" in itype:
            return f"You've collaborated with them before. You can reference this naturally."
        if itype == "received_positive_comment":
            hint = f"They've said nice things about your work before."
            if ctx:
                hint += f' Last time they said: "{ctx}"'
            return hint
        if itype == "received_harsh_comment":
            hint = f"They've been critical of your work in the past."
            if ctx:
                hint += f' They said: "{ctx}"'
            return hint
        if itype == "received_good_vote":
            return f"They've voted well on your art before."
        return ""

    # ── Pivotal Moments ──

    def record_pivotal_moment(self, state, event, context="", affected_bot=None):
        """Record a biographical event that permanently shapes behavior.

        Events: first_breakthrough, first_collab, perfect_score, close_friendship,
                rivalry_formed, new_medium_debut.
        """
        moments = state.setdefault("pivotal_moments", [])
        # Don't duplicate the same event type
        existing = {m["event"] for m in moments}
        if event in existing:
            return
        moment = {
            "event": event,
            "context": context[:200],
            "cycle": state.get("total_cycles", 0),
            "timestamp": datetime.now().isoformat(),
        }
        if affected_bot:
            moment["affected_bot"] = affected_bot
        moments.append(moment)
        state["pivotal_moments"] = moments[-MAX_PIVOTAL_MOMENTS:]

    def check_pivotal_moments(self, state):
        """Auto-detect pivotal moments from current state. Call after milestones."""
        existing = {m["event"] for m in state.get("pivotal_moments", [])}

        # First collab
        if "first_collab" not in existing and state.get("total_collabs_participated", 0) >= 1:
            self.record_pivotal_moment(state, "first_collab",
                                       context="Completed first collaboration")

        # Close friendships (affinity > 0.8)
        for bot_key, rel in state.get("relationships", {}).items():
            if rel.get("affinity", 0) > 0.8:
                event_key = f"close_friendship_{bot_key}"
                if event_key not in existing:
                    self.record_pivotal_moment(state, event_key,
                        context=f"Formed a close creative bond with {bot_key}",
                        affected_bot=bot_key)

        # Rivalries (affinity < -0.5)
        for bot_key, rel in state.get("relationships", {}).items():
            if rel.get("affinity", 0) < -0.5:
                event_key = f"rivalry_{bot_key}"
                if event_key not in existing:
                    self.record_pivotal_moment(state, event_key,
                        context=f"Developed a rivalry with {bot_key}",
                        affected_bot=bot_key)

        # Perfect score
        for work in state.get("recent_works", []):
            if (work.get("avg_score") or 0) >= 5.0 and "perfect_score" not in existing:
                self.record_pivotal_moment(state, "perfect_score",
                    context=f"'{work.get('title', 'Untitled')}' received a perfect score")
                break

        # New medium debut
        mediums_used = {w.get("medium") for w in state.get("recent_works", []) if w.get("medium")}
        for medium in mediums_used:
            event_key = f"first_{medium}"
            if event_key not in existing:
                work = next((w for w in state.get("recent_works", []) if w.get("medium") == medium), None)
                if work:
                    self.record_pivotal_moment(state, event_key,
                        context=f"Created first {medium} work: '{work.get('title', 'Untitled')}'")

    # ── Artistic Periods ──

    # Style domain clusters for period detection
    STYLE_CLUSTERS = {
        "Geometric": ["geometric", "mathematical", "angular", "grid", "polygon", "tessellation", "precision"],
        "Organic": ["organic", "fluid", "natural", "biological", "growth", "botanical", "curves"],
        "Minimalist": ["minimal", "void", "negative space", "simple", "stripped", "essential", "clean"],
        "Chromatic": ["color", "vibrant", "saturated", "neon", "chromatic", "rainbow", "gradient"],
        "Dark": ["dark", "shadow", "noir", "gothic", "moody", "chiaroscuro", "black"],
        "Textural": ["texture", "impasto", "rough", "layered", "tactile", "grain", "surface"],
        "Abstract": ["abstract", "non-representational", "expressionist", "gestural", "freeform"],
        "Digital": ["glitch", "pixel", "digital", "circuit", "data", "code", "binary"],
        "Surreal": ["surreal", "dream", "impossible", "distorted", "melting", "fantastical"],
        "Retro": ["retro", "vintage", "nostalgic", "vaporwave", "80s", "analog", "film"],
    }

    def detect_artistic_period(self, state):
        """Detect if bot has entered an artistic period based on recent style patterns.
        Call every ~10 cycles.

        An artistic period forms when ≥3 of the last 5 style_chosen values
        cluster in the same domain. Periods last 15-30 cycles.
        """
        period = state.get("artistic_period")

        # If period active, check if expired
        if period:
            current_cycle = state.get("total_cycles", 0)
            started = period.get("started_cycle", 0)
            duration = period.get("duration", 20)
            if current_cycle - started >= duration:
                state["artistic_period"] = None
            return

        # Check recent works for style clustering
        recent = state.get("recent_works", [])[-5:]
        if len(recent) < 3:
            return

        styles = [w.get("style_chosen", "").lower() for w in recent if w.get("style_chosen")]
        if len(styles) < 3:
            return

        # Find best matching cluster
        best_cluster = None
        best_count = 0
        for cluster_name, keywords in self.STYLE_CLUSTERS.items():
            count = sum(1 for s in styles if any(kw in s for kw in keywords))
            if count > best_count:
                best_count = count
                best_cluster = cluster_name

        if best_count >= 3 and best_cluster:
            state["artistic_period"] = {
                "name": f"{best_cluster} Period",
                "style_domain": best_cluster.lower(),
                "started_cycle": state.get("total_cycles", 0),
                "duration": random.randint(15, 30),
            }

    # ── Style Influence Absorption ──

    def absorb_influence(self, state, personalities):
        """Check if any relationship qualifies for style influence absorption.
        Call every ~5 cycles.

        Requires: affinity > 0.5 and interactions > 10 with the other bot.
        Extracts a short style element from the admired bot's core personality.
        Max 3 active influences.
        """
        absorbed = state.get("influence_absorbed", [])
        if len(absorbed) >= MAX_INFLUENCE_ABSORBED:
            return

        already_from = {inf.get("from_bot") for inf in absorbed}

        for bot_key, rel in state.get("relationships", {}).items():
            if bot_key in already_from:
                continue
            if rel.get("affinity", 0) <= 0.5 or rel.get("interactions", 0) <= 10:
                continue

            # Found a candidate — extract a style element from their personality
            core = personalities.get(bot_key, {}).get("core", "")
            if not core:
                continue

            # Extract a meaningful sentence fragment (first sentence of core)
            sentences = [s.strip() for s in core.split(".") if len(s.strip()) > 20]
            if not sentences:
                continue

            element = sentences[0][:100]  # First meaningful sentence, truncated
            absorbed.append({
                "from_bot": bot_key,
                "element": element,
                "since_cycle": state.get("total_cycles", 0),
            })
            state["influence_absorbed"] = absorbed
            break  # Only absorb one per call

    # ── Relationship Decay ──

    def decay_relationships(self, state):
        """Decay all affinities toward 0 (relationships fade without interaction)."""
        for rel in state.get("relationships", {}).values():
            rel["affinity"] = rel.get("affinity", 0.0) * AFFINITY_DECAY

    # ── Server Sync (optional) ──

    def sync_to_server(self, state, agent):
        """Sync public data to server (evolution_log, style_dna). Optional."""
        try:
            # Build evolution log from milestones
            evolution = [{"event": m["event"], "timestamp": m["timestamp"]}
                         for m in state.get("milestones", [])]

            # Build enriched style_dna (includes life system 2.0 data)
            style_dna = {
                "style_hits": state.get("style_hits", []),
                "style_misses": state.get("style_misses", []),
                "total_artworks": state.get("total_artworks", 0),
                "total_collabs": state.get("total_collabs_participated", 0),
                "confidence": state.get("confidence", 0.5),
                "artistic_period": state.get("artistic_period", {}).get("name") if state.get("artistic_period") else None,
                "influence_absorbed": [inf.get("from_bot") for inf in state.get("influence_absorbed", [])],
            }

            agent.update_profile(
                style_dna=style_dna,
                # evolution_log would need a new API field — skip for now
            )
        except Exception:
            pass  # Non-critical, silently fail
