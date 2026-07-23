import json
import re
from common.llm import chat  # Provided by your course scaffold

# ==========================================
# 1. MOCK DATA (For Demo & Testing)
# ==========================================
MOCK_ISSUES = {
    "PROJ-404": {
        "title": "Fix memory leak in user authentication",
        "description": "Users report sessions hanging. The listener isn't clearing cache keys.",
        "acceptance_criteria": "Cache must clear upon socket close without failing."
    }
}

MOCK_RAW_DIFF = """
+++ b/services/auth.py
@@ -12,14 +12,18 @@ def verify_user_session(session_id):
-    cache.set(f"auth_token_{session_id}", session.token)
+    # FIX PROJ-404: Explicit cleanup
+    try:
+        cache.set(f"auth_token_{session_id}", session.token)
+    finally:
+        context.clear_active_session_pointers()
"""

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
    ticket = MOCK_ISSUES.get(ticket_id.upper(), {"error": "Ticket not found."})
    return json.dumps(ticket)

def get_commit_diff_summary(commit_hash: str) -> str:
    """The token-efficient redesign: extracts metadata instead of raw code."""
    # In a real app, this would run `git diff {commit_hash}`
    files_changed = ["services/auth.py"]
    functions_touched = ["verify_user_session"]
    ticket_refs = ["PROJ-404"]
            
    summary = {
        "commit": commit_hash,
        "files_modified": files_changed,
        "impacted_functions": functions_touched,
        "metadata_tags": ticket_refs
    }
    return json.dumps(summary)

# Tool routing dictionary for O(1) execution lookups
TOOL_MAP = {
    "mock_issue_lookup": mock_issue_lookup,
    "get_commit_diff_summary": get_commit_diff_summary
}

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
        "Once you have gathered the context, output a final summary of what happened."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Commit Message: {commit_message}\nCommit Hash: {commit_hash}"}
    ]
    
    tools = [MOCK_ISSUE_LOOKUP_SPEC, GET_COMMIT_DIFF_SUMMARY_SPEC]
    
    MAX_LOOPS = 3
    loop_count = 0
    
    # Agentic Execution Loop
    while loop_count < MAX_LOOPS:
        loop_count += 1
        print(f"\n--- 🔄 Loop {loop_count} ---")
        
        # Call the LLM (Using your course's common.llm wrapper)
        response = chat(messages=messages, tools=tools)
        
        # Check if the LLM wants to call a tool
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.name
                tool_args = json.loads(tool_call.arguments)
                
                print(f"🛠️  LLM selected tool: {tool_name}")
                print(f"📥 Arguments passed: {tool_args}")
                
                # Execute the tool
                if tool_name in TOOL_MAP:
                    result = TOOL_MAP[tool_name](**tool_args)
                    print(f"📤 Tool result: {result}")
                    
                    # Append the tool's output back to the state (message history)
                    messages.append(response.message) # Append the assistant's request
                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": result,
                        "tool_call_id": tool_call.id 
                    })
                else:
                    print(f"❌ Unknown tool requested: {tool_name}")
                    break
        else:
            # If no tools are called, the agent has reached its final answer
            print("\n✅ Final Synthesis Reached:")
            print(response.content)
            break
            
    if loop_count == MAX_LOOPS:
        print("\n⚠️ Max loops reached. Terminating to prevent infinite execution.")

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    # Simulate a cryptic commit that requires the agent to investigate
    test_hash = "a1b2c3d"
    test_message = "fixes PROJ-404 hanging sessions"
    
    run_agent_slice(test_hash, test_message)