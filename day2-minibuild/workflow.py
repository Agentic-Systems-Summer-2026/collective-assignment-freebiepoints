import sys, pathlib
sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')

from common.llm import chat, STATS

# Read the notes file
with open('day2-minibuild/notes.txt', 'r') as f:
    notes_content = f.read()

print("Original notes:")
print(notes_content)
print("\n" + "="*50 + "\n")

# Step 1: Extract every action item from the notes (simplified approach)
try:
    response1 = chat([
        {"role": "system", "content": "Extract action items from the meeting notes. Return in format: 'Task: [description] | Owner: [person] | Deadline: [date]'"},
        {"role": "user", "content": f"Meeting notes:\n{notes_content}"}
    ], model="Qwen3 Coder 30B", temperature=0)
    
    print("Step 1 - Action Items:")
    print(response1)
    print("\n" + "="*50 + "\n")
    
    # Step 2: Find items with missing info (this is simplified)
    response2 = chat([
        {"role": "system", "content": "From the action items below, identify which ones are missing an owner or deadline. Format output as 'Task: [description] | Owner: [PERSON/MISSING] | Deadline: [DATE/MISSING]'"},
        {"role": "user", "content": f"Action items:\n{response1}"}
    ], model="Qwen3 Coder 30B", temperature=0)
    
    print("Step 2 - Flagged Items:")
    print(response2)
    print("\n" + "="*50 + "\n")
    
    # Step 3: Summary
    response3 = chat([
        {"role": "system", "content": "Write a 3-sentence status summary based on the action items and flagged items"},
        {"role": "user", "content": f"Action items:\n{response1}\n\nFlagged items:\n{response2}"}
    ], model="Qwen3 Coder 30B", temperature=0)
    
    print("Step 3 - Status Summary:")
    print(response3)
    print("\n" + "="*50 + "\n")
    
    print("STATS:")
    print(STATS)
    
except Exception as e:
    print(f"Error during processing: {e}")
    print("STATS:", STATS)