import sys, pathlib
sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')

from common.llm import chat, STATS

def read_notes():
    """Returns the text of day2-minibuild/notes.txt"""
    with open('day2-minibuild/notes.txt', 'r') as f:
        return f.read()

def count_items(text):
    """Returns how many action items appear in the given text (simple line/bullet count)"""
    lines = text.strip().split('\n')
    # Count non-empty lines that start with a bullet or number (typical action item format)
    count = 0
    for line in lines:
        line = line.strip()
        if line and (line.startswith('-') or line.startswith('*') or line[0].isdigit()):
            count += 1
    return count

def save_output(text):
    """Writes text to day2-minibuild/agent_output.txt and returns 'saved'"""
    with open('day2-minibuild/agent_output.txt', 'w') as f:
        f.write(text)
    return "saved"

def main():
    # Get the initial notes
    notes_text = read_notes()
    
    print("Processing meeting notes with agent-style approach...")
    
    # Define the system prompt that contains all instructions
    system_prompt = f"""You are an expert assistant analyzing meeting notes. Your goal is:
1. Extract action items from meeting notes with owner/deadline information
2. Mark items with missing owners or deadlines as MISSING 
3. Provide a professional 3-sentence status summary

Follow this exact protocol:
1. First, extract all action items in format "Task: [description] | Owner: [person/MISSING] | Deadline: [date/MISSING]"  
2. Then identify which items are missing owner or deadline information (they should be flagged as MISSING)
3. Finally, write a 3-sentence professional status summary

Current meeting notes:
{notes_text}

Please provide your response in the exact format required. Do NOT include any explanations, just the requested information."""

    # Make a single call with proper structure to avoid the bedrock issue
    try:
        final_response = chat([
            {"role": "user", "content": system_prompt}
        ], model="Qwen3 Coder 30B", temperature=0)
        
        print("Final Analysis Result:")
        print("=" * 50)
        print(final_response)
        print("=" * 50)
        print("\nSTATS:")
        print(STATS)
        
        # Also save to file
        save_output(final_response)
        print("\nOutput saved to day2-minibuild/agent_output.txt")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        print("STATS:", STATS)

if __name__ == "__main__":
    main()