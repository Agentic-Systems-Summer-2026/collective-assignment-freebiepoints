import sys, pathlib
sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')
import re

from common.llm import chat, STATS

def read_notes():
    """Returns the text of day2-minibuild/notes.txt"""
    with open('day2-minibuild/notes.txt', 'r') as f:
        return f.read()

def count_items(text):
    """Returns how many action items appear in text.

    Supports both bullet/numbered lists and plain-prose meeting notes.
    """
    lines = text.strip().split('\n')
    count = 0

    # First pass: explicit bullets/numbered items.
    for line in lines:
        line = line.strip()
        if line and (line.startswith('-') or line.startswith('*') or line[0].isdigit()):
            count += 1

    if count > 0:
        return count

    # Second pass: plain prose heuristics for meeting-note action commitments.
    text_lower = text.lower()
    patterns = [
        r'\bwill\s+(call|send|confirm|fix|schedule|draft|prepare|follow up|follow-up)\b',
        r'\bto\s+(call|send|confirm|fix|schedule|draft|prepare|follow up|follow-up)\b',
        r'\bneed\s+someone\s+to\s+schedule\b',
        r'\bsaid\s+he\'d\s+fix\b',
        r'\bsaid\s+she\'d\s+fix\b',
    ]
    matches = set()
    for pat in patterns:
        for m in re.finditer(pat, text_lower):
            matches.add((m.start(), m.end()))
    return len(matches)

def save_output(text):
    """Writes text to day2-minibuild/agent_output.txt and returns 'saved'"""
    with open('day2-minibuild/agent_output.txt', 'w') as f:
        f.write(text)
    return "saved"

def parse_reply(reply):
    """
    Forgiving reply parser that tolerates case differences, extra whitespace,
    conversational preamble, and markdown code fences.
    """
    # Normalize the reply by removing markdown code fences and standardizing whitespace
    normalized = reply.strip()
    
    # Remove markdown code fences if present
    if normalized.startswith("```"):
        lines = normalized.split('\n')
        if len(lines) > 2:
            normalized = '\n'.join(lines[1:-1]) if lines[-1] == '```' else normalized
        else:
            normalized = normalized.strip('` \n')
    
    # Preserve full multiline DONE payload if present.
    done_match = re.search(r'(?ims)^DONE\s*:\s*(.*)$', normalized)
    if done_match:
        return ('DONE', None, done_match.group(1).strip())

    # Parse command-like lines only to avoid accidental matches in conversational text.
    commands = []
    for line in normalized.splitlines():
        line = line.strip()
        m = re.match(r'^(ACTION|DONE)\s*:\s*(.*)$', line, flags=re.IGNORECASE)
        if m:
            commands.append((m.group(1).upper(), m.group(2).strip()))

    for kind, payload in commands:
        if kind == 'ACTION':
            tool_call = payload
            tool_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$', tool_call)
            if tool_match:
                return ('ACTION', tool_match.group(1), tool_match.group(2))
            # Fallback: action with function name but no parentheses.
            bare_name = tool_call.split()[0] if tool_call else ''
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', bare_name):
                return ('ACTION', bare_name, '')
    
    # If neither found, return None to indicate continuation needed
    return None, None, None

def main():
    # Get the initial notes
    notes_text = read_notes()
    
    # System prompt with goal and tool description
    system_prompt = f"""You are a task automation agent working on meeting notes analysis. Your goal is to:
1. Extract action items from the meeting notes with owner/deadline information
2. Identify items with missing owners or deadlines (flag them as MISSING)
3. Write a 3-sentence status summary

You have access to three tools:
- read_notes() - returns the full text of day2-minibuild/notes.txt
- count_items(text) - counts action items in a text (bulleted items)
- save_output(text) - saves text to day2-minibuild/agent_output.txt and returns "saved"

Reply each turn with either:
ACTION: tool_name(arguments)
DONE: <final answer>

Always use the exact format:
ACTION: function_name(arguments)
or
DONE: <final answer>

Never mix both formats in one reply.

Current meeting notes:
{notes_text}"""

    # Start conversation with system + user messages.
    # Some providers reject requests that contain only system messages.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Begin by choosing an ACTION or return DONE with the final result."}
    ]
    
    turn_count = 0
    max_turns = 8
    last_action_signature = None
    repeated_action_count = 0
    
    while turn_count < max_turns:
        turn_count += 1
        
        # Get model response
        # Let common.llm choose the provider-appropriate default model.
        model_response = chat(messages, temperature=0)
        messages.append({"role": "assistant", "content": model_response})
        
        print(f"Turn {turn_count} - Model Response:")
        print(model_response)
        print()
        
        # Parse reply
        reply_type, tool_name, args_str = parse_reply(model_response)
        
        if reply_type == 'DONE':
            final_answer = args_str
            print("Final Answer:")
            print(final_answer)
            break
        elif reply_type == 'ACTION' and tool_name:
            action_signature = f"{tool_name}({args_str})"
            if action_signature == last_action_signature:
                repeated_action_count += 1
            else:
                repeated_action_count = 1
                last_action_signature = action_signature

            # Execute the tool
            try:
                if tool_name == 'read_notes':
                    result = read_notes()
                elif tool_name == 'count_items':
                    arg = (args_str or '').strip()
                    if arg in ('read_notes()', 'read_notes'):
                        result = count_items(read_notes())
                    elif arg:
                        # Accept quoted strings, but also allow raw text if model omits quotes.
                        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                            arg = arg[1:-1]
                        result = count_items(arg)
                    else:
                        result = count_items(read_notes())
                elif tool_name == 'save_output':
                    if args_str:
                        result = save_output(args_str)
                    else:
                        result = "No text to save"
                else:
                    result = f"Unknown tool: {tool_name}"
                
                print(f"Tool {tool_name} result: {result}")
                
                # Append the tool result to conversation
                messages.append({"role": "user", "content": f"Tool result: {result}"})

                # Prevent infinite loops on repeated identical calls.
                if repeated_action_count >= 3:
                    messages.append({
                        "role": "user",
                        "content": "You already have the needed tool results. Return DONE with the final answer now."
                    })
                
            except Exception as e:
                error_msg = f"Tool error: {str(e)}"
                print(error_msg)
                messages.append({"role": "user", "content": error_msg})
            
        else:
            # If no recognized command, add a reminder
            print("No recognized command found. Adding reminder.")
            messages.append({"role": "user", "content": "Remember: Reply each turn with either ACTION: tool_name(arguments) or DONE: <final answer>."})
    
    print(f"\nCompleted after {turn_count} turns")
    print("STATS:")
    print(STATS)

if __name__ == "__main__":
    main()