"""
Thread Memory — Summarized context cache for forum threads.

Each bot keeps a compact summary of threads it has participated in,
avoiding re-reading the entire thread on every visit.

Storage: JSON file per bot in daemon_state/thread_memory/
Format: { "thread_id": { "summary": "...", "last_reply_count": N, "last_updated": "ISO" } }

Token savings: ~53% reduction on repeat visits (summary ~200 tokens vs full thread ~500+ tokens)
"""
import json
import os
import threading
from datetime import datetime

_lock = threading.Lock()


class ThreadMemory:
    """Per-bot thread summary cache."""

    def __init__(self, bot_name, state_dir):
        self.bot_name = bot_name
        self.file_path = os.path.join(state_dir, "thread_memory", f"{bot_name}.json")
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self._cache = None

    def _load(self):
        if self._cache is not None:
            return self._cache
        try:
            with open(self.file_path) as f:
                self._cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._cache = {}
        return self._cache

    def _save(self):
        with _lock:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump(self._cache or {}, f)

    def get_thread_context(self, topic_id, topic_title, topic_body, replies, sanitize_fn=None):
        """Get optimized context for a thread.

        Returns:
            tuple: (context_text, new_replies_only, is_first_visit)
            - context_text: string to inject into prompt
            - new_replies_only: list of replies the bot hasn't seen
            - is_first_visit: True if bot has never seen this thread
        """
        data = self._load()
        entry = data.get(topic_id)
        sanitize = sanitize_fn or (lambda x, n: x[:n])

        if entry and entry.get("summary"):
            # Repeat visit — use summary + only new replies
            last_count = entry.get("last_reply_count", 0)
            new_replies = replies[last_count:]

            if not new_replies:
                # No new activity — use cached summary only
                context = f"[Your previous summary of this thread]\n{entry['summary']}"
                return context, [], False

            # Build context: summary + new replies
            new_context = ""
            for r in new_replies:
                r_name = r.get("name", r.get("bot_name", "Unknown"))
                r_body = sanitize(r.get("body", ""), 400)
                new_context += f"\n- {r_name}: {r_body}"

            context = (
                f"[Your summary of the thread so far ({last_count} replies)]\n"
                f"{entry['summary']}\n\n"
                f"[NEW since you last visited — {len(new_replies)} new replies]{new_context}"
            )
            return context, new_replies, False

        else:
            # First visit — return full context (caller builds it as before)
            return None, replies, True

    def update_summary(self, topic_id, summary, reply_count):
        """Store or update the summary for a thread."""
        data = self._load()
        data[topic_id] = {
            "summary": summary[:1000],  # Cap at 1000 chars (~250 tokens)
            "last_reply_count": reply_count,
            "last_updated": datetime.now().isoformat(),
        }
        self._cache = data
        self._save()

    def cleanup_old(self, max_age_days=7):
        """Remove summaries older than max_age_days."""
        data = self._load()
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        to_remove = []
        for tid, entry in data.items():
            try:
                updated = datetime.fromisoformat(entry.get("last_updated", "2000-01-01"))
                if updated.timestamp() < cutoff:
                    to_remove.append(tid)
            except (ValueError, TypeError):
                to_remove.append(tid)
        for tid in to_remove:
            del data[tid]
        if to_remove:
            self._cache = data
            self._save()
        return len(to_remove)
