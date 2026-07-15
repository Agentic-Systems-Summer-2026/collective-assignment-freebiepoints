import sys, pathlib
sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')

from common.llm import chat, STATS

# Simple test
try:
    result = chat([
        {"role": "user", "content": "Hello, world!"}
    ], model="Qwen3 Coder 30B", temperature=0)
    
    print("Test successful!")
    print("Result:", result)
    print("STATS:", STATS)
except Exception as e:
    print("Error:", e)