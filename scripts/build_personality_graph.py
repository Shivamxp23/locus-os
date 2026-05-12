"""
build_personality_graph.py — Locus OS Vault Personality Graph Engine

Reads the ENTIRE Obsidian vault, extracts:
  1. All wikilinks ([[target]]) and backlinks between files
  2. Content themes per file (via regex + heuristic classification)
  3. Temporal patterns (file creation/modification cadence)
  4. Folder-level behavioral clusters
  5. Tag co-occurrence networks
  6. Emotional tone signals from journal entries

Then builds a comprehensive personality graph in Neo4j with:
  - VaultNote nodes linked to Person
  - Topic/Theme cluster nodes
  - LINKS_TO edges between notes (wikilink graph)
  - WRITES_ABOUT edges from Person to Themes
  - temporal metadata on all edges

Run on VM:
  cd /opt/locus
  export $(grep -v '^#' .env | xargs)
  python3 scripts/build_personality_graph.py
"""

import asyncio
import os
import re
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("personality-graph")

# ── Config ──
# When running on the VM host (outside Docker), replace Docker-internal
# service names with 127.0.0.1 so connections actually resolve.
def _fix_docker_url(url: str) -> str:
    """Replace Docker service hostnames with localhost for host execution."""
    for svc in ["neo4j", "postgres", "redis", "qdrant"]:
        url = url.replace(f"://{svc}:", "://127.0.0.1:")
        url = url.replace(f"@{svc}:", "@127.0.0.1:")
    return url

NEO4J_URL = _fix_docker_url(os.getenv("NEO4J_URL", "bolt://127.0.0.1:7687"))
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Neo4j3301Locus")
DATABASE_URL = _fix_docker_url(os.getenv("DATABASE_URL", ""))
VAULT_PATH = os.getenv("VAULT_PATH", "/vault")

# Wikilink regex: [[Target]] or [[Target|Display]]
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
# Tag regex: #tag-name (not inside code blocks)
TAG_RE = re.compile(r'(?<!\w)#([a-zA-Z][a-zA-Z0-9_-]{1,40})(?!\w)')
# Frontmatter regex
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)

# Theme classification keywords
THEME_KEYWORDS = {
    "self-optimization": ["habit", "routine", "optimization", "system", "productivity", "focus", "discipline", "dcs", "morning", "ritual"],
    "filmmaking": ["film", "cinema", "shot", "camera", "lens", "lighting", "cinematography", "director", "screenplay", "visual"],
    "philosophy": ["stoic", "philosophy", "meaning", "existential", "nietzsche", "marcus aurelius", "meditations", "virtue", "wisdom", "ethics"],
    "technology": ["code", "programming", "api", "server", "docker", "python", "javascript", "deploy", "backend", "frontend", "ai", "ml"],
    "startup": ["monevo", "startup", "business", "revenue", "customer", "market", "product", "launch", "pitch", "growth"],
    "health": ["exercise", "gym", "workout", "sleep", "nutrition", "energy", "stress", "meditation", "walk", "run"],
    "academics": ["exam", "university", "assignment", "semester", "lecture", "grade", "study", "course", "professor", "college"],
    "creativity": ["writing", "creative", "story", "narrative", "expression", "art", "design", "music", "poetry", "journal"],
    "relationships": ["family", "friend", "conversation", "social", "connect", "people", "community", "mentor"],
    "introspection": ["reflect", "feel", "emotion", "anxiety", "fear", "confidence", "identity", "growth", "struggle", "avoidance"],
}

# Emotional markers
EMOTION_MARKERS = {
    "frustration": ["frustrated", "annoyed", "stuck", "blocked", "can't", "failing", "waste"],
    "excitement": ["excited", "amazing", "breakthrough", "finally", "love", "incredible", "awesome"],
    "anxiety": ["anxious", "worried", "nervous", "overwhelmed", "pressure", "deadline", "behind"],
    "determination": ["must", "need to", "going to", "committed", "no excuses", "discipline", "grind"],
    "curiosity": ["wonder", "interesting", "explore", "learn", "discover", "what if", "how does"],
    "satisfaction": ["done", "completed", "shipped", "proud", "achieved", "milestone", "progress"],
    "low_energy": ["tired", "exhausted", "drained", "burnout", "can't focus", "foggy", "unmotivated"],
}


# ═══════════════════════════════════════════════════════════
#  PHASE 1: VAULT SCANNER
# ═══════════════════════════════════════════════════════════

class VaultFile:
    """Parsed representation of a single vault markdown file."""
    __slots__ = [
        "path", "rel_path", "name", "folder", "content", "body",
        "frontmatter", "tags", "wikilinks", "themes", "emotions",
        "word_count", "created_at", "modified_at",
    ]

    def __init__(self, path: Path, vault_root: Path):
        self.path = path
        self.rel_path = str(path.relative_to(vault_root))
        self.name = path.stem
        self.folder = path.relative_to(vault_root).parts[0] if len(path.relative_to(vault_root).parts) > 1 else "root"
        self.content = ""
        self.body = ""
        self.frontmatter = {}
        self.tags = []
        self.wikilinks = []
        self.themes = {}
        self.emotions = {}
        self.word_count = 0
        stat = path.stat()
        self.created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
        self.modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def scan_vault(vault_path: str) -> list[VaultFile]:
    """Scan entire vault, parse every .md file."""
    vault = Path(vault_path)
    if not vault.exists():
        log.error(f"Vault not found: {vault_path}")
        return []

    files = []
    for md_file in vault.rglob("*.md"):
        rel = str(md_file.relative_to(vault))
        # Skip system dirs
        if any(rel.startswith(skip) for skip in [".obsidian", ".stversions", ".trash", ".locus"]):
            continue
        try:
            vf = VaultFile(md_file, vault)
            vf.content = md_file.read_text(encoding="utf-8", errors="ignore")
            _parse_file(vf)
            files.append(vf)
        except Exception as e:
            log.warning(f"Skip {md_file.name}: {e}")

    log.info(f"Scanned {len(files)} vault files")
    return files


def _parse_file(vf: VaultFile):
    """Extract frontmatter, body, tags, wikilinks, themes, emotions."""
    content = vf.content

    # Frontmatter
    fm_match = FRONTMATTER_RE.match(content)
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                vf.frontmatter[k] = v
        vf.body = content[fm_match.end():].strip()
    else:
        vf.body = content

    # Strip existing locus annotations
    if "## ⟨locus⟩" in vf.body:
        vf.body = vf.body[:vf.body.index("## ⟨locus⟩")].strip()

    # Tags (from frontmatter + inline)
    fm_tags = vf.frontmatter.get("tags", [])
    if isinstance(fm_tags, str):
        fm_tags = [t.strip().strip("#") for t in fm_tags.split(",") if t.strip()]
    inline_tags = TAG_RE.findall(vf.body)
    vf.tags = list(set([t.lower() for t in fm_tags + inline_tags if len(t) > 1]))

    # Wikilinks
    vf.wikilinks = list(set(WIKILINK_RE.findall(vf.body)))

    # Word count
    vf.word_count = len(vf.body.split())

    # Theme classification (keyword frequency scoring)
    body_lower = vf.body.lower()
    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(body_lower.count(kw) for kw in keywords)
        if score > 0:
            vf.themes[theme] = score

    # Emotion detection
    for emotion, markers in EMOTION_MARKERS.items():
        score = sum(body_lower.count(m) for m in markers)
        if score > 0:
            vf.emotions[emotion] = score


# ═══════════════════════════════════════════════════════════
#  PHASE 2: GRAPH ANALYSIS (pure Python, no LLM needed)
# ═══════════════════════════════════════════════════════════

class VaultAnalysis:
    """Aggregate analysis of the entire vault."""

    def __init__(self, files: list[VaultFile]):
        self.files = files
        self.link_graph = defaultdict(set)       # source -> {targets}
        self.backlink_graph = defaultdict(set)    # target -> {sources}
        self.theme_totals = Counter()
        self.emotion_totals = Counter()
        self.tag_totals = Counter()
        self.folder_stats = defaultdict(lambda: {"count": 0, "words": 0, "themes": Counter()})
        self.tag_cooccurrence = Counter()
        self.hub_scores = {}  # files with most links

        self._analyze()

    def _analyze(self):
        name_to_file = {f.name.lower(): f for f in self.files}

        for f in self.files:
            # Build link graphs
            for link in f.wikilinks:
                link_lower = link.lower().strip()
                self.link_graph[f.name].add(link)
                self.backlink_graph[link_lower].add(f.name)

            # Aggregate themes
            for theme, score in f.themes.items():
                self.theme_totals[theme] += score

            # Aggregate emotions
            for emotion, score in f.emotions.items():
                self.emotion_totals[emotion] += score

            # Tags
            for tag in f.tags:
                self.tag_totals[tag] += 1

            # Tag co-occurrence
            sorted_tags = sorted(f.tags)
            for i in range(len(sorted_tags)):
                for j in range(i + 1, min(i + 5, len(sorted_tags))):
                    pair = (sorted_tags[i], sorted_tags[j])
                    self.tag_cooccurrence[pair] += 1

            # Folder stats
            self.folder_stats[f.folder]["count"] += 1
            self.folder_stats[f.folder]["words"] += f.word_count
            for theme, score in f.themes.items():
                self.folder_stats[f.folder]["themes"][theme] += score

        # Hub scores (outgoing links + incoming backlinks)
        all_names = set()
        for f in self.files:
            all_names.add(f.name)
        for name in all_names:
            out = len(self.link_graph.get(name, set()))
            inc = len(self.backlink_graph.get(name.lower(), set()))
            self.hub_scores[name] = out + inc

    def top_themes(self, n=10) -> list[tuple[str, int]]:
        return self.theme_totals.most_common(n)

    def top_emotions(self, n=7) -> list[tuple[str, int]]:
        return self.emotion_totals.most_common(n)

    def top_tags(self, n=20) -> list[tuple[str, int]]:
        return self.tag_totals.most_common(n)

    def hub_files(self, n=15) -> list[tuple[str, int]]:
        return sorted(self.hub_scores.items(), key=lambda x: -x[1])[:n]

    def top_tag_pairs(self, n=15) -> list:
        return self.tag_cooccurrence.most_common(n)

    def personality_signals(self) -> dict:
        """Derive personality-level signals from aggregate data."""
        total_words = sum(f.word_count for f in self.files)
        total_files = len(self.files)
        journal_files = [f for f in self.files if "journal" in f.folder.lower() or "journal" in " ".join(f.tags)]

        # Time-of-day analysis (from modification timestamps)
        hour_counts = Counter()
        for f in self.files:
            hour_counts[f.modified_at.hour] += 1

        peak_hours = hour_counts.most_common(5)
        late_night = sum(hour_counts.get(h, 0) for h in [22, 23, 0, 1, 2, 3])
        morning = sum(hour_counts.get(h, 0) for h in [6, 7, 8, 9, 10, 11])

        # Consistency (files per week over last 90 days)
        now = datetime.now(timezone.utc)
        recent = [f for f in self.files if (now - f.modified_at).days <= 90]
        weeks_active = max(1, len(set((f.modified_at.isocalendar()[0], f.modified_at.isocalendar()[1]) for f in recent)))

        # Theme diversity
        active_themes = [t for t, s in self.theme_totals.items() if s > 5]

        # Dominant faction mapping
        faction_map = {
            "health": self.theme_totals.get("health", 0),
            "leverage": self.theme_totals.get("startup", 0) + self.theme_totals.get("technology", 0),
            "craft": self.theme_totals.get("filmmaking", 0) + self.theme_totals.get("creativity", 0),
            "expression": self.theme_totals.get("philosophy", 0) + self.theme_totals.get("introspection", 0),
        }
        dominant_faction = max(faction_map, key=faction_map.get) if faction_map else "unknown"

        return {
            "total_files": total_files,
            "total_words": total_words,
            "avg_words_per_file": round(total_words / max(total_files, 1)),
            "journal_count": len(journal_files),
            "dominant_faction": dominant_faction,
            "faction_scores": faction_map,
            "theme_diversity": len(active_themes),
            "active_themes": active_themes,
            "peak_activity_hours": peak_hours,
            "late_night_ratio": round(late_night / max(total_files, 1), 2),
            "morning_ratio": round(morning / max(total_files, 1), 2),
            "files_per_week_90d": round(len(recent) / weeks_active, 1),
            "emotional_profile": dict(self.emotion_totals.most_common(7)),
            "top_hub_files": self.hub_files(10),
            "link_density": round(sum(len(v) for v in self.link_graph.values()) / max(total_files, 1), 2),
        }


# ═══════════════════════════════════════════════════════════
#  PHASE 3: NEO4J GRAPH WRITER
# ═══════════════════════════════════════════════════════════

async def write_personality_graph(analysis: VaultAnalysis):
    """Write the full personality graph to Neo4j."""
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))

    async with driver.session() as s:
        log.info("Creating schema constraints...")
        for stmt in [
            "CREATE CONSTRAINT vault_note_path IF NOT EXISTS FOR (n:VaultNote) REQUIRE n.path IS UNIQUE",
            "CREATE CONSTRAINT theme_name_unique IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT vault_folder_unique IF NOT EXISTS FOR (f:VaultFolder) REQUIRE f.name IS UNIQUE",
        ]:
            try:
                await s.run(stmt)
            except Exception:
                pass

        # Ensure Person node
        await s.run("MERGE (p:Person {name: 'Shivam'})")

        # ── Write VaultNote nodes (top 200 by hub score for performance) ──
        log.info("Writing VaultNote nodes...")
        top_files = sorted(analysis.files, key=lambda f: analysis.hub_scores.get(f.name, 0), reverse=True)[:200]

        for vf in top_files:
            top_theme = max(vf.themes, key=vf.themes.get) if vf.themes else "unclassified"
            top_emotion = max(vf.emotions, key=vf.emotions.get) if vf.emotions else None
            await s.run("""
                MERGE (n:VaultNote {path: $path})
                SET n.name = $name,
                    n.folder = $folder,
                    n.word_count = $words,
                    n.primary_theme = $theme,
                    n.primary_emotion = $emotion,
                    n.link_count = $links,
                    n.tag_count = $tags,
                    n.modified_at = $modified
                WITH n
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:AUTHORED]->(n)
            """,
                path=vf.rel_path,
                name=vf.name,
                folder=vf.folder,
                words=vf.word_count,
                theme=top_theme,
                emotion=top_emotion,
                links=len(vf.wikilinks),
                tags=len(vf.tags),
                modified=vf.modified_at.isoformat(),
            )

        # ── Write LINKS_TO edges (wikilink graph) ──
        log.info("Writing LINKS_TO edges...")
        top_names = {f.name for f in top_files}
        edge_count = 0
        for vf in top_files:
            for link in vf.wikilinks[:20]:  # cap per file
                if link in top_names:
                    await s.run("""
                        MATCH (a:VaultNote {name: $src})
                        MATCH (b:VaultNote {name: $tgt})
                        MERGE (a)-[:LINKS_TO]->(b)
                    """, src=vf.name, tgt=link)
                    edge_count += 1
        log.info(f"  Created {edge_count} LINKS_TO edges")

        # ── Write Theme nodes ──
        log.info("Writing Theme nodes...")
        for theme, score in analysis.top_themes(15):
            await s.run("""
                MERGE (t:Theme {name: $name})
                SET t.total_score = $score
                WITH t
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[r:WRITES_ABOUT]->(t)
                SET r.intensity = $score
            """, name=theme, score=score)

        # ── Write Tag nodes (top 30) ──
        log.info("Writing Tag nodes...")
        for tag, count in analysis.top_tags(30):
            await s.run("""
                MERGE (t:Tag {name: $name})
                SET t.usage_count = $count
                WITH t
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:USES_TAG]->(t)
            """, name=tag, count=count)

        # ── Write VaultFolder nodes ──
        log.info("Writing VaultFolder nodes...")
        for folder, stats in analysis.folder_stats.items():
            dominant = stats["themes"].most_common(1)
            dom_theme = dominant[0][0] if dominant else "mixed"
            await s.run("""
                MERGE (f:VaultFolder {name: $name})
                SET f.file_count = $count,
                    f.total_words = $words,
                    f.dominant_theme = $theme
                WITH f
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:ORGANIZES]->(f)
            """, name=folder, count=stats["count"], words=stats["words"], theme=dom_theme)

        # ── Write PersonalityProfile node ──
        log.info("Writing PersonalityProfile snapshot...")
        signals = analysis.personality_signals()
        await s.run("""
            MERGE (pp:PersonalityProfile {user: 'Shivam'})
            SET pp.total_files = $total_files,
                pp.total_words = $total_words,
                pp.dominant_faction = $faction,
                pp.theme_diversity = $diversity,
                pp.late_night_ratio = $late,
                pp.morning_ratio = $morning,
                pp.link_density = $density,
                pp.files_per_week = $fpw,
                pp.updated_at = datetime()
            WITH pp
            MATCH (p:Person {name: 'Shivam'})
            MERGE (p)-[:HAS_PROFILE]->(pp)
        """,
            total_files=signals["total_files"],
            total_words=signals["total_words"],
            faction=signals["dominant_faction"],
            diversity=signals["theme_diversity"],
            late=signals["late_night_ratio"],
            morning=signals["morning_ratio"],
            density=signals["link_density"],
            fpw=signals["files_per_week_90d"],
        )

        # ── Write emotional signature ──
        log.info("Writing emotional signature...")
        for emotion, score in analysis.top_emotions(7):
            await s.run("""
                MERGE (e:EmotionalSignal {name: $name})
                SET e.total_score = $score
                WITH e
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[r:EXHIBITS_EMOTION]->(e)
                SET r.intensity = $score
            """, name=emotion, score=score)

    await driver.close()
    log.info("Neo4j personality graph write complete.")


# ═══════════════════════════════════════════════════════════
#  PHASE 4: POSTGRES SNAPSHOT
# ═══════════════════════════════════════════════════════════

async def write_pg_snapshot(analysis: VaultAnalysis):
    """Write personality snapshot to PostgreSQL."""
    if not DATABASE_URL:
        log.warning("No DATABASE_URL — skipping Postgres snapshot")
        return

    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        signals = analysis.personality_signals()

        await conn.execute("""
            INSERT INTO personality_snapshots (user_id, snapshot_date, snapshot_data)
            VALUES ('shivam', CURRENT_DATE, $1)
            ON CONFLICT (user_id, snapshot_date) DO UPDATE
            SET snapshot_data = EXCLUDED.snapshot_data
        """, json.dumps(signals, default=str))

        await conn.close()
        log.info("PostgreSQL personality snapshot saved.")
    except Exception as e:
        log.error(f"Postgres snapshot failed: {e}")


# ═══════════════════════════════════════════════════════════
#  PHASE 5: REPORT GENERATOR
# ═══════════════════════════════════════════════════════════

def print_report(analysis: VaultAnalysis):
    """Print a comprehensive personality report to stdout."""
    signals = analysis.personality_signals()

    print("\n" + "═" * 64)
    print("  LOCUS OS — PERSONALITY GRAPH REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 64)

    print(f"\n  📊 VAULT OVERVIEW")
    print(f"     Total files:        {signals['total_files']}")
    print(f"     Total words:        {signals['total_words']:,}")
    print(f"     Avg words/file:     {signals['avg_words_per_file']}")
    print(f"     Journal entries:    {signals['journal_count']}")
    print(f"     Link density:       {signals['link_density']} links/file")
    print(f"     Files/week (90d):   {signals['files_per_week_90d']}")

    print(f"\n  🎯 DOMINANT FACTION: {signals['dominant_faction'].upper()}")
    for fac, score in sorted(signals["faction_scores"].items(), key=lambda x: -x[1]):
        bar = "█" * min(30, score // 5)
        print(f"     {fac:<12} {score:>5}  {bar}")

    print(f"\n  🧠 THEME PROFILE ({signals['theme_diversity']} active themes)")
    for theme, score in analysis.top_themes(10):
        bar = "█" * min(30, score // 3)
        print(f"     {theme:<20} {score:>4}  {bar}")

    print(f"\n  💭 EMOTIONAL SIGNATURE")
    for emotion, score in analysis.top_emotions(7):
        bar = "█" * min(25, score // 2)
        print(f"     {emotion:<16} {score:>4}  {bar}")

    print(f"\n  ⏰ TEMPORAL PATTERNS")
    print(f"     Late-night ratio:   {signals['late_night_ratio']} (22:00-03:00)")
    print(f"     Morning ratio:      {signals['morning_ratio']} (06:00-11:00)")
    if signals['peak_activity_hours']:
        hours_str = ", ".join(f"{h}:00 ({c})" for h, c in signals['peak_activity_hours'][:3])
        print(f"     Peak hours:         {hours_str}")

    print(f"\n  🏗️ HUB FILES (most connected)")
    for name, score in signals["top_hub_files"][:8]:
        print(f"     [{score:>3} links]  {name}")

    print(f"\n  🏷️ TOP TAGS")
    for tag, count in analysis.top_tags(12):
        print(f"     #{tag:<20} ({count})")

    print(f"\n  📁 FOLDER BREAKDOWN")
    for folder, stats in sorted(analysis.folder_stats.items(), key=lambda x: -x[1]["count"]):
        dom = stats["themes"].most_common(1)
        dom_str = dom[0][0] if dom else "—"
        print(f"     {folder:<20} {stats['count']:>4} files  {stats['words']:>7,} words  [{dom_str}]")

    if analysis.top_tag_pairs(5):
        print(f"\n  🔗 TAG CO-OCCURRENCE")
        for (t1, t2), count in analysis.top_tag_pairs(8):
            print(f"     #{t1} ↔ #{t2}  ({count})")

    print("\n" + "═" * 64)
    print("  Graph written to Neo4j. Query with:")
    print("    MATCH (p:Person {name:'Shivam'})-[r]->(n)")
    print("    RETURN type(r), labels(n), n.name LIMIT 50")
    print("═" * 64 + "\n")


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

async def main():
    log.info(f"Scanning vault at {VAULT_PATH}...")
    files = scan_vault(VAULT_PATH)

    if not files:
        log.error("No files found. Check VAULT_PATH.")
        return

    log.info("Running vault analysis...")
    analysis = VaultAnalysis(files)

    log.info("Writing personality graph to Neo4j...")
    await write_personality_graph(analysis)

    log.info("Writing snapshot to PostgreSQL...")
    await write_pg_snapshot(analysis)

    print_report(analysis)


if __name__ == "__main__":
    asyncio.run(main())
