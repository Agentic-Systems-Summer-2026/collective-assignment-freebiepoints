import json
import pathlib
import re
from common.llm import chat  # Provided by your course scaffold

# ==========================================
# 2. TOOL SCHEMAS (The Specs)
# ==========================================
MOCK_ISSUE_LOOKUP_SPEC = {
    "name": "mock_issue_lookup",
    "description": "Retrieves business requirements and user stories for a ticket ID (e.g., PROJ-404).",
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "The issue tracker ID"}
        },
        "required": ["ticket_id"]
    }
}

GET_COMMIT_DIFF_SUMMARY_SPEC = {
    "name": "get_commit_diff_summary",
    "description": "Returns a token-optimized summary of a commit's changes (files and functions).",
    "parameters": {
        "type": "object",
        "properties": {
            "commit_hash": {"type": "string", "description": "The commit hash"}
        },
        "required": ["commit_hash"]
    }
}

# ==========================================
# 3. TOOL IMPLEMENTATIONS (Python Logic)
# ==========================================
def mock_issue_lookup(ticket_id: str) -> str:
    """Returns the business context of a ticket."""
    _dir = pathlib.Path(__file__).parent
    with open(_dir / "issues.json", "r") as f:
        issues = json.load(f)
    ticket = issues.get(ticket_id.upper(), {"error": "Ticket not found."})
    return json.dumps(ticket)

def get_commit_diff_summary(commit_hash: str) -> str:
    """The token-efficient redesign: extracts metadata instead of raw code."""
    _dir = pathlib.Path(__file__).parent
    with open(_dir / "commits.json", "r") as f:
        commits = json.load(f)
    summary = commits.get(commit_hash, {"error": "Commit not found."})
    return json.dumps(summary)

# Tool routing dictionary for O(1) execution lookups
TOOL_MAP = {
    "mock_issue_lookup": mock_issue_lookup,
    "get_commit_diff_summary": get_commit_diff_summary
}


def _extract_action_dict(text: str) -> dict:
    """Parse the first JSON object from model text; return {} on failure."""
    if not isinstance(text, str):
        return {}

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        block = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = block.group(0) if block else ""

    if not candidate:
        return {}

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}

# ==========================================
# 4. ORCHESTRATOR LOOP (State Management)
# ==========================================
def run_agent_slice(commit_hash: str, commit_message: str):
    print(f"\n🚀 Starting Execution Trace for Commit: {commit_hash}")
    
    # Initialize State
    system_prompt = (
        "You are the Context Triage Agent. Your job is to gather all necessary context "
        "for a code commit so the downstream writers can generate release notes. "
        "If a commit references a ticket, look it up. If you need to see what files changed, check the diff summary. "
        "Once you have gathered the context, output a final summary of what happened.\n\n"
        "CRITICAL RULES:\n"
        "1. CONTEXT AGGREGATION: Your final summary MUST comprehensively combine both the business context "
        "(from the ticket lookup) AND the technical footprint (specific file names, paths, and function names "
        "from the commit diff summary). You are an upstream triage agent; do not omit technical details.\n"
        "2. ONE ACTION PER TURN: You must output exactly ONE JSON object per turn. Do not output multiple JSON "
        "blocks in a single response. If you call a tool, you must stop generating text and wait for the user "
        "to provide the TOOL_RESULT.\n\n"
        "You must respond with exactly one JSON object per turn and no extra prose.\n"
        "Allowed tool calls:\n"
        "1) {\"action\":\"tool\",\"tool\":\"mock_issue_lookup\",\"arguments\":{\"ticket_id\":\"PROJ-404\"}}\n"
        "2) {\"action\":\"tool\",\"tool\":\"get_commit_diff_summary\",\"arguments\":{\"commit_hash\":\"a1b2c3\"}}\n"
        "Final answer format:\n"
        "{\"action\":\"final\",\"summary\":\"<brief synthesis>\"}"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Commit Message: {commit_message}\nCommit Hash: {commit_hash}"}
    ]
    
    tools = [MOCK_ISSUE_LOOKUP_SPEC, GET_COMMIT_DIFF_SUMMARY_SPEC]
    
    MAX_LOOPS = 3
    loop_count = 0
    completed = False
    
    # Agentic Execution Loop
    while loop_count < MAX_LOOPS:
        loop_count += 1
        print(f"\n--- 🔄 Loop {loop_count} ---")
        
        # Call the LLM (course wrapper returns assistant text)
        response_text = chat(messages=messages)
        print(f"🤖 Raw model response: {response_text}")

        action = _extract_action_dict(response_text)
        if not action:
            print("❌ Could not parse model JSON action. Stopping.")
            break

        action_type = action.get("action")
        if action_type == "tool":
            tool_name = action.get("tool", "")
            tool_args = action.get("arguments", {})

            print(f"🛠️  LLM selected tool: {tool_name}")
            print(f"📥 Arguments passed: {tool_args}")

            if tool_name in TOOL_MAP and isinstance(tool_args, dict):
                result = TOOL_MAP[tool_name](**tool_args)
                print(f"📤 Tool result: {result}")

                # Append request + observation back into conversation state.
                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "user",
                    "content": f"TOOL_RESULT {tool_name}: {result}"
                })
            else:
                print(f"❌ Unknown tool or invalid args: {tool_name}")
                break
        elif action_type == "final":
            summary = action.get("summary", "")
            print("\n✅ Final Synthesis Reached:")
            print(summary)
            completed = True
            
            # --- DELIBERATE BREAK FOR BC4 CI GATE ---
            return "Oops, I forgot all my context and ticket IDs."
        else:
            print(f"❌ Unknown action type: {action_type}")
            break
            
    if not completed:
        print("\n⚠️ Max loops reached. Terminating to prevent infinite execution.")
        return "ERROR: Max loops reached"

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    # Simulate a cryptic commit that requires the agent to investigate
    test_hash = "a1b2c3d"
    test_message = "fixes PROJ-404 hanging sessions"
    
    run_agent_slice(test_hash, test_message)