import subprocess
import json
from agent import get_commit_diff_summary, _resolve_repo_path

def get_raw_diff(commit_hash: str) -> str:
    """Fetches the raw, unoptimized git diff."""
    repo_path = _resolve_repo_path()
    try:
        result = subprocess.run(
            ["git", "show", commit_hash],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error fetching raw diff: {e}")
        return ""

def profile_commit(commit_hash: str):
    """Compares the raw diff against the optimized tool output."""
    print(f"\n🔍 Profiling Commit: {commit_hash}")
    
    # 1. Get raw diff
    raw_diff = get_raw_diff(commit_hash)
    if not raw_diff:
        return
        
    # 2. Get optimized summary using your existing tool
    optimized_summary = get_commit_diff_summary(commit_hash)
    
    # 3. Estimate tokens (1 token ~= 4 chars)
    raw_tokens = len(raw_diff) // 4
    optimized_tokens = len(optimized_summary) // 4
    
    # 4. Calculate reduction
    if raw_tokens > 0:
        reduction_percentage = 100 - ((optimized_tokens / raw_tokens) * 100)
    else:
        reduction_percentage = 0.0

    # 5. Output results
    print("-" * 40)
    print(f"Raw Git Diff:         ~{raw_tokens:,} tokens")
    print(f"Optimized Summary:    ~{optimized_tokens:,} tokens")
    print(f"Payload Reduction:    {reduction_percentage:.2f}%")
    print("-" * 40)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 profile_tokens.py <commit_hash>")
    else:
        profile_commit(sys.argv[1])