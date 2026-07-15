import sys, pathlib
sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')

from common.llm import chat, STATS

def read_notes():
    """Returns the text of day2-minibuild/notes.txt"""
    with open('day2-minibuild/notes.txt', 'r') as f:
        return f.read()

def count_items(text):
    """Returns how many action items appear in the given text (implement as a simple line/bullet count)"""
    lines = text.strip().split('\n')
    # Count non-empty lines that start with a bullet or number or dash
    count = 0
    for line in lines:
        line = line.strip()
        if line and (line.startswith('-') or line.startswith('*') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.') or line.startswith('6.') or line.startswith('7.') or line.startswith('8.') or line.startswith('9.')):
            count += 1
    return count

def save_output(text):
    """Writes text to day2-minibuild/agent_output.txt and returns "saved" """
    with open('day2-minibuild/agent_output.txt', 'w') as f:
        f.write(text)
    return "saved"

def parse_reply(reply):
    """
    Forgiving reply parser that tolerates case differences, extra whitespace,
    conversational preamble, and markdown code fences.
    """
    # Normalize reply by stripping and removing markdown if present
    normalized = reply.strip()
    
    # Remove markdown code fences if present
    if normalized.startswith("```"):
        lines = normalized.split('\n')
        if len(lines) >= 3 and lines[-1] == '```':
            normalized = '\n'.join(lines[1:-1])
        else:
            normalized = normalized.lstrip('` \n')
    normalized = normalized.strip()
    
    # Search for either ACTION or DONE anywhere in the text (case insensitive)
    reply_lower = normalized.lower()
    
    # Check for ACTION first
    action_pos = reply_lower.find('action:')
    if action_pos != -1:
        action_part = normalized[action_pos:]
        # Find the tool name and arguments
        colon_pos = action_part.find(':')
        if colon_pos != -1:
            tool_call = action_part[colon_pos + 1:].strip()
            # Find opening parenthesis
            paren_open = tool_call.find('(')
            if paren_open != -1:
                tool_name = tool_call[:paren_open].strip()
                # Find closing parenthesis
                paren_close = tool_call.rfind(')')
                if paren_close != -1:
                    args_str = tool_call[paren_open + 1:paren_close].strip()
                    return 'ACTION', tool_name, args_str
                else:
                    # If no closing paren, take everything after opening paren
                    args_str = tool_call[paren_open + 1:].strip()
                    return 'ACTION', tool_name, args_str
            else:
                # Just the function name with no args
                tool_name = tool_call.strip()
                return 'ACTION', tool_name, ''
    
    # Check for DONE
    done_pos = reply_lower.find('done:')
    if done_pos != -1:
        done_part = normalized[done_pos:]
        return 'DONE', None, done_part[5:].strip()  # Remove 'DONE:' prefix
    
    # If no recognized command found
    return None, None, None

def main():
    # Get the initial notes
    notes_text = read_notes()
    
    # System prompt with detailed instructions
    system_prompt = f"""You are a task automation agent working on meeting notes analysis. Your goal is:
1. Extract all action items from the meeting notes 
2. For each item, provide: Task description | Owner (or MISSING) | Deadline (or MISSING)
3. Identify which items are missing owners or deadlines and flag them
4. Write a 3-sentence professional status summary

YOU HAVE ACCESS TO THESE THREE TOOLS:
- read_notes() - returns the full text of day2-minibuild/notes.txt
- count_items(text) - counts action items in text (bullet/numbered items)
- save_output(text) - saves text to day2-minibuild/agent_output.txt and returns "saved"

YOUR RESPONSE FORMAT:
Each turn, you must reply with EITHER:
ACTION: tool_name(arguments) 
OR
DONE: <final comprehensive answer>

When you do ACTION, I will execute the tool and return its result instantly for you to use in subsequent steps.

IMPORTANT: Do not include any additional text, explanation, or markdown formatting. 
Just follow the exact format shown above.

PROCESSING NOTES:
{notes_text}"""

    # Initialize conversation
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    turn_count = 0
    max_turns = 8
    
    print("Starting agent execution...")
    print("=" * 60)
    
    while turn_count < max_turns:
        turn_count += 1
        print(f"\nTURN {turn_count}")
        print("-" * 30)
        
        # Get model response  
        try:
            model_response = chat(messages, model="Qwen3 Coder 30B", temperature=0)
            print("MODEL RESPONSE:")
            print(model_response)
        except Exception as e:
            print(f"MODEL ERROR ON TURN {turn_count}: {e}")
            # Try with default fallback prompt
            default_prompt = "Please analyze the meeting notes carefully and provide the action items with owners/deadlines, flagged missing information, and 3-sentence status summary. Format the final response as requested."
            model_response = chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": default_prompt}
            ], model="Qwen3 Coder 30B", temperature=0)
            print("RECOVERY MODEL RESPONSE:")
            print(model_response)
        
        # Parse reply
        reply_type, tool_name, args_str = parse_reply(model_response)
        
        if reply_type == 'DONE':
            final_answer = args_str
            print(f"\nFINAL ANSWER RECEIVED ON TURN {turn_count}")
            print("=" * 60)
            print(final_answer)
            print("=" * 60)
            
            # Save the final output
            save_output(final_answer)
            print("Output saved to day2-minibuild/agent_output.txt")
            break
            
        elif reply_type == 'ACTION' and tool_name:
            print(f"EXECUTING TOOL: {tool_name}({args_str})")
            
            try:
                result = ""
                if tool_name == 'read_notes':
                    result = read_notes()
                elif tool_name == 'count_items':
                    result = str(count_items(notes_text))  # Using our main notes text
                elif tool_name == 'save_output':
                    if args_str:
                        result = save_output(args_str)
                    else:
                        result = "No content to save"
                else:
                    result = f"ERROR: Unknown tool '{tool_name}'"
                
                print(f"TOOL RESULT: {result}")
                
                # Append tool result to conversation
                messages.append({"role": "user", "content": f"TOOL RESULT: {result}"})
                
            except Exception as e:
                error_result = f"ERROR EXECUTING {tool_name}: {str(e)}"
                print(f"TOOL ERROR: {error_result}")
                messages.append({"role": "user", "content": f"TOOL ERROR: {error_result}"})
                
        else:
            print("NO RECOGNIZED COMMAND FOUND. REPLYING WITH REMINDER.")
            messages.append({"role": "user", "content": "REMINDER: Please use either 'ACTION: tool_name(arguments)' or 'DONE: <final answer>' format exactly as specified."})
    
    print(f"\nAGENT COMPLETED AFTER {turn_count} TURNS")
    print("STATS:")
    print(STATS)
    
    # If we reached max turns without DONE, provide the last response
    if turn_count >= max_turns and reply_type != 'DONE':
        print("MAX TURNS REACHED WITHOUT FINAL RESPONSE")

if __name__ == "__main__":
    main()