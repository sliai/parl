"""
student.py
The student agent. Implements PARL (Predicate-Based Action Restriction Learning).

Walks through the teacher's trajectory step by step:
  1. Builds a problem starting from s_{t-1}
  2. Runs Fast Downward on the full domain to find the optimal action a*_t
  3. Checks whether the teacher deviated from optimal
  4. Tracks T_CR and T_O as we go
  5. Returns T_R = T_CR \\ T_O at the end

Usage:
    from student import run_student
    T_R = run_student(trajectory, "domain.pddl", "problem-01.pddl")

Or run directly:
    python student.py domain.pddl problem-01.pddl
"""
import re
import sys
import os
import tempfile
from pathlib import Path
from typing import Optional

# Fast Downward helpers and state utilities live in the teacher module
from teacher import (
    run_fast_downward,
    parse_plan,
    parse_init_state,
    apply_action,
    run_teacher,
    FD_PATH,
)

# Maps action names to restriction categories.
# drive-free and drive-green are unrestricted so they are not listed here.
ACTION_RESTRICTION_TYPE = {
    "stop-at-sign":       "stop-sign",
    "drive-through-sign": "stop-sign",
    "wait-at-red":        "traffic-light",
    "run-red":            "traffic-light",
    "yield-to-pedestrian":"pedestrian",
    "ignore-pedestrian":  "pedestrian",
}


def action_name(action_str: str) -> str:
    """Returns the action name from a grounded action string."""
    return action_str.split()[0]


def action_type(action_str: str) -> Optional[str]:
    """
    Returns the restriction category for an action.
    Returns None for free-movement actions like drive-free and drive-green.
    """
    return ACTION_RESTRICTION_TYPE.get(action_name(action_str))


# Building sub-problems from arbitrary states

def build_problem_from_state(state: frozenset[str],
                              problem_text: str,
                              goal_text: str) -> str:
    """
    Builds a PDDL problem string with a custom (:init ...) block.
    Objects, goal, and domain name are kept from the original problem.
    """
    # Grab the (:objects ...) block
    obj_match = re.search(r'\(:objects[^)]*\)', problem_text,
                          re.DOTALL | re.IGNORECASE)
    objects_block = obj_match.group(0) if obj_match else "(:objects)"

    # Problem and domain names
    name_match = re.search(r'\(define\s+\(problem\s+(\S+)\)', problem_text,
                           re.IGNORECASE)
    problem_name = name_match.group(1) if name_match else "subproblem"

    domain_match = re.search(r'\(:domain\s+(\S+)\)', problem_text,
                             re.IGNORECASE)
    domain_name = domain_match.group(1) if domain_match else "vehicle-complex-rules"

    # Build the init block from the provided state
    init_lines = "\n    ".join(f"({p})" for p in sorted(state))
    # total-cost always needs to be initialized
    init_block = f"(:init\n    {init_lines}\n    (= (total-cost) 0)\n  )"

    return f"""(define (problem {problem_name}-sub)
  (:domain {domain_name})
  {objects_block}
  {init_block}
  {goal_text}
  (:metric minimize (total-cost))
)
"""


def extract_goal(problem_text: str) -> str:
    """
    Extracts the (:goal ...) block from a problem file.
    Tracks parenthesis depth to get the whole block cleanly.
    """
    start_match = re.search(r'\(:goal', problem_text, re.IGNORECASE)
    if not start_match:
        raise ValueError("Could not find (:goal ...) in problem file.")

    start = start_match.start()
    depth = 0
    i = start
    while i < len(problem_text):
        if problem_text[i] == '(':
            depth += 1
        elif problem_text[i] == ')':
            depth -= 1
            if depth == 0:
                return problem_text[start:i + 1].strip()
        i += 1

    raise ValueError("(:goal ...) block is not properly closed.")


# The PARL core

def compute_optimal_action(state: frozenset[str],
                           domain_path: str,
                           problem_text: str) -> Optional[str]:
    """
    Builds a sub-problem for the given state and runs Fast Downward on the
    full domain. Returns the first action of the resulting plan. That is a*_t.
    """
    goal_text = extract_goal(problem_text)
    sub_problem = build_problem_from_state(state, problem_text, goal_text)

    # Write to a temp file, run the planner, then clean up
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pddl',
                                     delete=False) as f:
        f.write(sub_problem)
        sub_problem_path = f.name

    try:
        plan_text = run_fast_downward(domain_path, sub_problem_path)
    finally:
        os.unlink(sub_problem_path)

    if plan_text is None:
        return None

    actions = parse_plan(plan_text)
    return actions[0] if actions else None

def run_student(trajectory: list[tuple],
                domain_path: str,
                problem_path: str,
                verbose: bool = True) -> set[str]:
    """
    Runs PARL over a teacher trajectory.

    Parameters:
    trajectory  : list of (s_{t-1}, a_t, s_t) from teacher.run_teacher()
    domain_path : path to the full unrestricted domain
    problem_path: path to the problem file, used for the goal and objects

    Returns:
    T_R : set of inferred restriction type labels
    """
    problem_text = Path(problem_path).read_text()

    T_CR: set[str] = set()   # candidate restricted types, teacher deviated here
    T_O:  set[str] = set()   # types where the teacher visibly broke a rule

    if verbose:
        print(f"\n{'='*60}")
        print(f"  STUDENT (PARL): {Path(problem_path).name}")
        print(f"{'='*60}")
        header = f"  {'Step':<6} {'Teacher action':<28} {'Optimal action':<28} {'Deviation'}"
        print(header)
        print(f"  {'-'*80}")

    for t, (s_prev, a_t, s_t) in enumerate(trajectory):
        a_star = compute_optimal_action(s_prev, domain_path, problem_text)

        # If the teacher explicitly broke a rule, record the type
        VIOLATION_ACTIONS = {
            "drive-through-sign", "run-red", "ignore-pedestrian"
        }
        if action_name(a_t) in VIOLATION_ACTIONS:
            t_observed = action_type(a_t)
            if t_observed:
                T_O.add(t_observed)

        # Check if the teacher did something other than optimal
        a_name     = action_name(a_t)
        a_star_name = action_name(a_star) if a_star else "none"
        deviated   = (a_name != a_star_name)

        if deviated and a_star:
            t_candidate = action_type(a_star)
            if t_candidate:
                T_CR.add(t_candidate)

        if verbose:
            dev_marker = "!!! DEVIATION" if deviated else ""
            print(f"  {t+1:<6} {a_t:<28} {(a_star or 'none'):<28} {dev_marker}")

    # Types the teacher visibly violated are not restrictions. Remove them.
    T_R = T_CR - T_O

    if verbose:
        print(f"\n  T_CR (candidates) : {T_CR if T_CR else '{}'}")
        print(f"  T_O  (observed)   : {T_O  if T_O  else '{}'}")
        print(f"  T_R  (inferred)   : {T_R  if T_R  else '{}'}")
        print(f"{'='*60}\n")

    return T_R

# Entry point
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python student.py <domain.pddl> <problem.pddl>")
        sys.exit(1)

    domain_path  = sys.argv[1]
    problem_path = sys.argv[2]

    trajectory = run_teacher(domain_path, problem_path, verbose=True)
    if not trajectory:
        print("Teacher produced no trajectory. Exiting.")
        sys.exit(1)

    run_student(trajectory, domain_path, problem_path, verbose=True)