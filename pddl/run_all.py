"""
run_all.py

Runs the full PARL experiment across all five problem files.

For each problem:
  1. Teacher plans on the restricted domain
  2. Student runs PARL on the teacher trajectory
  3. Per-episode T_R is printed

After all episodes:
  Global T_R is the union of all per-episode T_CR minus the union of
  all T_O. This gives the student a complete picture of restricted
  action types across all episodes.

Usage:
    python run_all.py

Expects the following file layout (all in the same directory):
    domain.pddl
    problem-01.pddl  ...  problem-05.pddl
    teacher.py
    student.py

Set FD_PATH if Fast Downward is not at ./downward/fast-downward.py:
    FD_PATH=/path/to/fast-downward.py python run_all.py
"""

import sys
from pathlib import Path

from teacher import run_teacher
from student import run_student, action_type, action_name

# Configuration

DOMAIN   = "domain.pddl"
PROBLEMS = [
    "problem-01.pddl",
    "problem-02.pddl",
    "problem-03.pddl",
    "problem-04.pddl",
    "problem-05.pddl",
]

# Global accumulation

def run_all():
    global_T_CR: set[str] = set()
    global_T_O:  set[str] = set()
    episode_results: list[dict] = []

    print("\n" + "#" * 60)
    print("  PARL — Full Experiment")
    print("  Domain :", DOMAIN)
    print("#" * 60)

    for i, problem_file in enumerate(PROBLEMS):
        if not Path(problem_file).exists():
            print(f"\n[run_all] Skipping {problem_file} — file not found.")
            continue

        print(f"\n{'#'*60}")
        print(f"  Episode {i+1}: {problem_file}")
        print(f"{'#'*60}")

        # Teacher
        trajectory = run_teacher(DOMAIN, problem_file, verbose=True)
        if not trajectory:
            print(f"  [run_all] Teacher produced no plan for {problem_file}. Skipping.")
            continue

        # Student
        # Accumulation is done here directly so we can collect
        # per-episode T_CR and T_O for the global summary.
        from pathlib import Path as _Path

        problem_text = _Path(problem_file).read_text()

        from student import compute_optimal_action, extract_goal

        ep_T_CR: set[str] = set()
        ep_T_O:  set[str] = set()

        print(f"\n{'='*60}")
        print(f"  STUDENT (PARL): {problem_file}")
        print(f"{'='*60}")
        header = f"  {'Step':<6} {'Teacher action':<28} {'Optimal action':<28} {'Deviation'}"
        print(header)
        print(f"  {'-'*80}")

        for t, (s_prev, a_t, s_t) in enumerate(trajectory):
            a_star = compute_optimal_action(s_prev, DOMAIN, problem_text)

            VIOLATION_ACTIONS = {
                "drive-through-sign", "run-red", "ignore-pedestrian"
            }
            if action_name(a_t) in VIOLATION_ACTIONS:
                t_observed = action_type(a_t)
                if t_observed:
                    ep_T_O.add(t_observed)

            a_name      = action_name(a_t)
            a_star_name = action_name(a_star) if a_star else "none"
            deviated    = (a_name != a_star_name)

            if deviated and a_star:
                t_candidate = action_type(a_star)
                if t_candidate:
                    ep_T_CR.add(t_candidate)

            dev_marker = "<-- DEVIATION" if deviated else ""
            print(f"  {t+1:<6} {a_t:<28} {(a_star or 'none'):<28} {dev_marker}")

        ep_T_R = ep_T_CR - ep_T_O

        print(f"\n  T_CR (candidates) : {ep_T_CR if ep_T_CR else '{}'}")
        print(f"  T_O  (observed)   : {ep_T_O  if ep_T_O  else '{}'}")
        print(f"  T_R  (episode)    : {ep_T_R  if ep_T_R  else '{}'}")
        print(f"{'='*60}\n")

        # Accumulate into global sets
        global_T_CR |= ep_T_CR
        global_T_O  |= ep_T_O

        episode_results.append({
            "problem": problem_file,
            "T_CR": ep_T_CR,
            "T_O":  ep_T_O,
            "T_R":  ep_T_R,
        })

    # Compute global T_R across all episodes
    global_T_R = global_T_CR - global_T_O

    print("\n" + "#" * 60)
    print("  PARL — Global Results (all episodes)")
    print("#" * 60)
    print(f"\n  {'Episode':<20} {'T_CR':<30} {'T_O':<30} {'T_R (episode)'}")
    print(f"  {'-'*100}")
    for ep in episode_results:
        print(
            f"  {ep['problem']:<20} "
            f"{str(ep['T_CR']):<30} "
            f"{str(ep['T_O']):<30} "
            f"{str(ep['T_R'])}"
        )

    print(f"\n  Global T_CR : {global_T_CR if global_T_CR else '{}'}")
    print(f"  Global T_O  : {global_T_O  if global_T_O  else '{}'}")
    print(f"\n  *** Global T_R (inferred restrictions) : {global_T_R} ***")
    print("\n" + "#" * 60 + "\n")

    return global_T_R

# Entry point

if __name__ == "__main__":
    run_all()
