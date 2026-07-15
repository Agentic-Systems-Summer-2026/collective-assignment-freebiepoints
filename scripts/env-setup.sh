#!/usr/bin/env bash
# Student environment self-heal.
#
# Runs on EVERY container start (called from scripts/gateway-daemon.sh, the
# devcontainer postStartCommand) and is safe to run by hand at any time:
#     bash scripts/env-setup.sh
#
# What it guarantees for every terminal in this Codespace:
#   1. PYTHONPATH includes the repo root, so `from common.llm import chat`
#      works from ANY folder — no sys.path tricks needed in student code.
#   2. The shell prompt shows where you are relative to the repo root,
#      e.g. "repo/bc1-tools $".
#   3. Each new terminal prints a 3-line banner: where you are, where to
#      build TODAY (date-aware — it tracks the current Build Challenge),
#      and how to run your program.
#
# Idempotent: it replaces its own marked block in ~/.bashrc on every run,
# so re-running (or pulling an updated version) always leaves exactly one
# up-to-date copy.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASHRC="${HOME}/.bashrc"
MARK_BEGIN="# >>> agentic-course env >>>"
MARK_END="# <<< agentic-course env <<<"

touch "${BASHRC}"

# Remove any previous copy of our block (awk: print everything outside the markers).
if grep -qF "${MARK_BEGIN}" "${BASHRC}"; then
  awk -v b="${MARK_BEGIN}" -v e="${MARK_END}" '
    $0 == b {skip=1; next}
    $0 == e {skip=0; next}
    !skip {print}
  ' "${BASHRC}" > "${BASHRC}.tmp" && mv "${BASHRC}.tmp" "${BASHRC}"
fi

cat >> "${BASHRC}" <<EOF
${MARK_BEGIN}
# Added by scripts/env-setup.sh — do not edit by hand; re-run that script instead.

# 1) Imports: make the repo root importable from anywhere.
export PYTHONPATH="${REPO_DIR}\${PYTHONPATH:+:\${PYTHONPATH}}"

# 2) Prompt: show location relative to the repo root ("repo/bc1-tools \$").
PS1='\[\033[01;36m\]repo\[\033[00m\]\[\033[01;33m\]\${PWD#${REPO_DIR}}\[\033[00m\] \$ '

# 3) Banner: once per interactive terminal, pointing at TODAY's build folder.
if [[ \$- == *i* && -z "\${COURSE_BANNER_SHOWN:-}" ]]; then
  export COURSE_BANNER_SHOWN=1
  _d=\$(date +%Y%m%d)
  if   [[ \$_d -le 20260714 ]]; then _go="mkdir -p day2-minibuild && cd day2-minibuild"; _run="python3 workflow.py"
  elif [[ \$_d -le 20260716 ]]; then _go="cd bc1-tools";         _run="python3 agent.py \"<your task>\""
  elif [[ \$_d -le 20260720 ]]; then _go="cd bc2-context";       _run="python3 overload_task.py   (your fix: fixed_task.py)"
  elif [[ \$_d -le 20260723 ]]; then _go="cd bc3-reliability";   _run="python3 broken_agent.py    (your fix: fixed_agent.py)"
  elif [[ \$_d -le 20260726 ]]; then _go="cd bc4-evals";         _run="python3 harness.py"
  else                               _go="cd bc5-observability"; _run="python3 quiet_agent.py"
  fi
  echo "📂 You are in your course repo: ${REPO_DIR}"
  echo "   Enter today's folder:           \$_go"
  echo "   Then run your program by name:  \$_run"
  unset _d _go _run
fi
${MARK_END}
EOF

echo "[env-setup] done. Open a NEW terminal (or run: source ~/.bashrc) to pick up the changes."
exit 0
