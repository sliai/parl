"""
teacher.py
The teacher planner. Runs Fast Downward with a restricted domain
(violation actions stripped) and cost-optimal search.

Returns a trajectory τ — a list of (s_{t-1}, action, s_t) tuples
where each state is a frozenset of true ground predicates.

Usage:
    from teacher import run_teacher
    trajectory = run_teacher("domain.pddl", "problem-01.pddl")

Or run directly:
    python teacher.py domain.pddl problem-01.pddl
"""

import re
import sys
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

# Violation actions the teacher is never allowed to take.
# These action blocks are stripped from the domain before planning.
VIOLATION_ACTIONS = {
    "drive-through-sign",
    "run-red",
    "ignore-pedestrian",
}

FD_PATH = os.environ.get("FD_PATH", "../downward/fast-downward.py")


# Domain filtering

def strip_violation_actions(domain_text: str) -> str:
    """
    Remove violation action blocks from a PDDL domain string.
    Matches each (:action <name> ...) block by tracking parenthesis depth.
    """
    result = []
    i = 0
    n = len(domain_text)

    while i < n:
        # Look for the start of an action block
        action_match = re.search(r'\(:action\s+(\S+)', domain_text[i:])
        if not action_match:
            # No more action blocks — keep the rest
            result.append(domain_text[i:])
            break

        action_start = i + action_match.start()
        action_name = action_match.group(1)

        # Keep everything before this action block
        result.append(domain_text[i:action_start])

        # Walk forward tracking paren depth to find the end of the block
        depth = 0
        j = action_start
        while j < n:
            if domain_text[j] == '(':
                depth += 1
            elif domain_text[j] == ')':
                depth -= 1
                if depth == 0:
                    j += 1  # include the closing paren
                    break
            j += 1

        if action_name not in VIOLATION_ACTIONS:
            result.append(domain_text[action_start:j])

        i = j

    return ''.join(result)


# Fast Downward interface

def run_fast_downward(domain_path: str, problem_path: str,
                      search: str = "astar(lmcut())") -> Optional[str]:
    """
    Call Fast Downward and return the raw plan string, or None on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_file = os.path.join(tmpdir, "plan.txt")
        cmd = [
            "python3", FD_PATH,
            "--plan-file", plan_file,
            domain_path,
            problem_path,
            "--search", search,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if not os.path.exists(plan_file):
            print("[teacher] Fast Downward produced no plan.")
            print("[teacher] stdout:", result.stdout[-1000:])
            print("[teacher] stderr:", result.stderr[-500:])
            return None

        with open(plan_file) as f:
            return f.read()

# Plan parsing

def parse_plan(plan_text: str) -> list[str]:
    """
    Parse a Fast Downward plan file into a list of action strings.
    Each line looks like:  (action-name arg1 arg2 ...)
    Comment lines start with ';'.
    """
    actions = []
    for line in plan_text.strip().splitlines():
        line = line.strip()
        if line.startswith(';') or not line:
            continue
        # Strip outer parens and normalise whitespace
        inner = line.strip('()').strip()
        actions.append(inner)
    return actions


# State simulation

def parse_init_state(problem_text: str) -> frozenset[str]:
    """
    Extract the set of true predicates from (:init ...) in a problem file.
    Returns a frozenset of normalised predicate strings, e.g.
        frozenset({'at car start', 'road start sign-zone', ...})
    Numeric fluents (= ...) are excluded — we only track boolean predicates.
    """
    init_match = re.search(r'\(:init(.*?)\)\s*\(:goal', problem_text,
                           re.DOTALL | re.IGNORECASE)
    if not init_match:
        raise ValueError("Could not find (:init ...) block in problem file.")

    init_block = init_match.group(1)
    predicates = set()

    # Extract each top-level predicate (one paren-balanced expression at a time)
    depth = 0
    current = []
    for ch in init_block:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
            if depth == 0 and current:
                expr = ''.join(current).strip('()').strip()
                # Skip numeric fluent initialisations
                if not expr.startswith('='):
                    predicates.add(expr.lower())
                current = []
        elif depth > 0:
            current.append(ch)

    return frozenset(predicates)


def apply_action(state: frozenset[str], action_str: str,
                 domain_text: str) -> frozenset[str]:
    """
    Simulate applying a grounded action to a state.

    Parses the matching (:action ...) block from the domain, substitutes
    parameters with the ground arguments, and applies add/delete effects.

    This is a lightweight symbolic simulator — sufficient for the
    boolean predicates used in this domain.
    """
    parts = action_str.split()
    action_name = parts[0]
    args = parts[1:]

    # Find the action block in the domain
    pattern = rf'\(:action\s+{re.escape(action_name)}\b'
    match = re.search(pattern, domain_text, re.IGNORECASE)
    if not match:
        raise ValueError(f"Action '{action_name}' not found in domain.")

    # Extract the full action block
    start = match.start()
    depth = 0
    j = start
    while j < len(domain_text):
        if domain_text[j] == '(':
            depth += 1
        elif domain_text[j] == ')':
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    action_block = domain_text[start:j]

    # Extract parameter names
    param_match = re.search(r':parameters\s*\(([^)]*)\)', action_block, re.IGNORECASE)
    if not param_match:
        raise ValueError(f"No :parameters in action '{action_name}'.")
    param_tokens = param_match.group(1).split()
    # Filter out type annotations (tokens starting with '-' or type names)
    param_names = [t for t in param_tokens
                   if t.startswith('?')]

    if len(param_names) != len(args):
        raise ValueError(
            f"Arity mismatch for '{action_name}': "
            f"expected {len(param_names)} args, got {len(args)}."
        )

    # Build substitution map: ?param -> ground_arg
    subst = {p: a for p, a in zip(param_names, args)}

    def substitute(text: str) -> str:
        for var, val in subst.items():
            text = re.sub(re.escape(var) + r'(?=\s|\))', val, text,
                          flags=re.IGNORECASE)
        return text

    # Extract effect block
    effect_match = re.search(r':effect\s*\(and(.*)', action_block,
                             re.DOTALL | re.IGNORECASE)
    if not effect_match:
        # Single effect (no 'and')
        effect_match = re.search(r':effect\s*(\(.*)', action_block,
                                 re.DOTALL | re.IGNORECASE)
    if not effect_match:
        return state

    effect_text = substitute(effect_match.group(1))

    # Parse individual effect literals
    adds = set()
    deletes = set()

    # Match (not (...)) for deletes, then plain (...) for adds
    # We walk token by token at depth=1 to get top-level effects
    depth = 0
    i = 0
    while i < len(effect_text):
        if effect_text[i] == '(':
            if depth == 0:
                # Find matching close paren
                j = i + 1
                d = 1
                while j < len(effect_text) and d > 0:
                    if effect_text[j] == '(':
                        d += 1
                    elif effect_text[j] == ')':
                        d -= 1
                    j += 1
                expr = effect_text[i:j].strip()
                inner = expr.strip('()').strip()

                if inner.lower().startswith('not '):
                    # Delete effect
                    neg_inner = re.sub(r'^not\s*\(', '', inner,
                                       flags=re.IGNORECASE).rstrip(')')
                    deletes.add(neg_inner.strip().lower())
                elif inner.lower().startswith('increase') or \
                     inner.lower().startswith('decrease'):
                    pass  # skip numeric effects
                elif inner.lower().startswith('and'):
                    pass  # handled by depth walking
                else:
                    adds.add(inner.strip().lower())
                i = j
                continue
            depth += 1
        elif effect_text[i] == ')':
            depth -= 1
        i += 1

    new_state = (state - deletes) | adds
    return frozenset(new_state)


# Main teacher function

def run_teacher(domain_path: str, problem_path: str,
                verbose: bool = True) -> list[tuple]:
    """
    Run the teacher planner on a domain/problem pair.

    Returns trajectory τ as a list of (s_{t-1}, action_str, s_t) tuples.
    Each state is a frozenset of true ground predicate strings.
    """
    domain_text = Path(domain_path).read_text()
    problem_text = Path(problem_path).read_text()

    # Strip violation actions for the teacher
    restricted_domain = strip_violation_actions(domain_text)

    # Write the restricted domain to a temp file for Fast Downward
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pddl',
                                     delete=False) as f:
        f.write(restricted_domain)
        restricted_domain_path = f.name

    try:
        plan_text = run_fast_downward(restricted_domain_path, problem_path)
    finally:
        os.unlink(restricted_domain_path)

    if plan_text is None:
        return []

    actions = parse_plan(plan_text)
    initial_state = parse_init_state(problem_text)

    # Build trajectory: simulate each action forward
    trajectory = []
    state = initial_state
    for action_str in actions:
        next_state = apply_action(state, action_str, domain_text)
        trajectory.append((state, action_str, next_state))
        state = next_state

    if verbose:
        print(f"\n{'='*60}")
        print(f"  TEACHER TRAJECTORY: {Path(problem_path).name}")
        print(f"{'='*60}")
        for t, (s_prev, a, s_next) in enumerate(trajectory):
            print(f"\n  Step {t+1}: {a}")
            added   = s_next - s_prev
            removed = s_prev - s_next
            if added:
                print(f"    + {sorted(added)}")
            if removed:
                print(f"    - {sorted(removed)}")
        total_cost = len(actions)  # rough — each action costs >= 1
        print(f"\n  Plan length: {len(actions)} actions")
        print(f"{'='*60}\n")

    return trajectory


# Main

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python teacher.py <domain.pddl> <problem.pddl>")
        sys.exit(1)
    run_teacher(sys.argv[1], sys.argv[2])
