#!/usr/bin/env python3
"""Build Challenge 1 — tool-calling agent (extended).

Run:  cd bc1-tools && python3 agent.py "what's in my notes about the demo?"

Tools added (BC1 requirement):
  - search_notes_snippet : token-efficient replacement for search_notes_verbose
                           returns (filename, line_number, snippet) triples
  - word_count           : char + word count for one note or all notes
  - write_note           : create/overwrite a .txt file in data/

The verbose tool is kept for before/after comparison; STATS shows the delta.
"""
import json
import pathlib
import re
import sys

# common/ lives one level up
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common.llm import chat, load_prompt, STATS

DATA = pathlib.Path(__file__).resolve().parent / "data"
MAX_STEPS = 12

TOOLS_SPEC = """Available tools (reply with ONE JSON object per turn):

{"tool": "list_notes"}
  -> list filenames in the notes folder

{"tool": "search_notes_verbose", "query": "x"}
  -> FULL TEXT of every note containing x  [WASTEFUL — prefer search_notes_snippet]

{"tool": "search_notes_snippet", "query": "x"}
  -> [{\"file\": \"...\", \"line\": N, \"snippet\": \"...\"}] for each matching line
     (token-efficient: returns only the matching lines, not whole documents)

{"tool": "read_note", "name": "<file>"}
  -> full text of one note

{"tool": "word_count", "name": "<file>"}
  -> {"file": "...", "words": N, "chars": N} for one note
     omit "name" to get counts for ALL notes

{"tool": "write_note", "name": "<file>", "content": "<text>"}
  -> writes content to data/<file> (creates or overwrites); returns confirmation

{"tool": "finish", "answer": "<final answer>"}
  -> end the task with a one-sentence summary
"""


# ── tool implementations ────────────────────────────────────────────────────

def _safe_path(name: str) -> pathlib.Path:
    """Resolve a note name to a path safely inside DATA/."""
    return DATA / pathlib.Path(name).name


def tool_list_notes() -> str:
    return json.dumps(sorted(p.name for p in DATA.glob("*.txt")))


def tool_search_notes_verbose(query: str) -> str:
    """Original wasteful implementation — kept for before/after comparison."""
    q = query.lower()
    out = {p.name: p.read_text() for p in DATA.glob("*.txt")
           if q in p.read_text().lower()}
    return json.dumps(out) if out else "no matches"


def tool_search_notes_snippet(query: str) -> str:
    """Token-efficient search: returns only matching lines with context."""
    q = query.lower()
    hits = []
    for p in sorted(DATA.glob("*.txt")):
        for i, line in enumerate(p.read_text().splitlines(), start=1):
            if q in line.lower():
                hits.append({"file": p.name, "line": i, "snippet": line.strip()})
    return json.dumps(hits) if hits else "no matches"


def tool_word_count(name: str | None) -> str:
    """Return word and char counts for one note or all notes."""
    if name:
        p = _safe_path(name)
        if not p.exists():
            return "ERROR: no such note"
        text = p.read_text()
        return json.dumps({"file": p.name,
                           "words": len(text.split()),
                           "chars": len(text)})
    # all notes
    result = {}
    for p in sorted(DATA.glob("*.txt")):
        text = p.read_text()
        result[p.name] = {"words": len(text.split()), "chars": len(text)}
    return json.dumps(result)


def tool_write_note(name: str, content: str) -> str:
    """Write content to data/<name>. Creates or overwrites."""
    if not name.endswith(".txt"):
        name = name + ".txt"
    p = _safe_path(name)
    p.write_text(content)
    return f"OK: wrote {len(content)} chars to {p.name}"


def tool_read_note(name: str) -> str:
    p = _safe_path(name)
    return p.read_text() if p.exists() else "ERROR: no such note"


# ── dispatch ────────────────────────────────────────────────────────────────

def run_tool(act: dict) -> str:
    t = act.get("tool")
    if t == "list_notes":
        return tool_list_notes()
    if t == "search_notes_verbose":
        return tool_search_notes_verbose(act.get("query", "").lower())
    if t == "search_notes_snippet":
        return tool_search_notes_snippet(act.get("query", ""))
    if t == "read_note":
        return tool_read_note(act.get("name", ""))
    if t == "word_count":
        return tool_word_count(act.get("name"))
    if t == "write_note":
        return tool_write_note(act.get("name", "output.txt"),
                               act.get("content", ""))
    return "ERROR: unknown tool " + repr(t)


# ── main loop ───────────────────────────────────────────────────────────────

def main():
    task = " ".join(sys.argv[1:]) or \
        "Summarize what my notes say about the capstone demo."
    msgs = [
        {"role": "system", "content": load_prompt("bc1-agent-system.txt")},
        {"role": "user",   "content": TOOLS_SPEC + "\nTASK: " + task},
    ]
    for step in range(1, MAX_STEPS + 1):
        out = chat(msgs)
        m = re.search(r"\{.*\}", out, re.S)
        act = json.loads(m.group(0)) if m else {}
        preview = {k: v for k, v in act.items()
                   if k not in ("tool", "answer", "content")}
        print(f"── step {step}: request≈{sum(len(x['content']) for x in msgs)} chars"
              f" → chose {act.get('tool')} {preview}")
        if act.get("tool") == "finish":
            print("\nANSWER:", act.get("answer", ""))
            break
        obs = run_tool(act)
        print(f"          tool returned {len(obs)} chars")
        msgs += [
            {"role": "assistant", "content": out},
            {"role": "user",      "content": "OBSERVATION:\n" + obs},
        ]
    else:
        print("hit step limit without finishing")
    print(f"\nSTATS: {STATS}")


if __name__ == "__main__":
    main()
