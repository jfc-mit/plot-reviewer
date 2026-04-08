#!/usr/bin/env python3
"""
Plot feedback loop — review and polish physics plots to publication quality.

Architecture:
  1. Haiku mechanical spec check → executor fix if needed
  2. 3 parallel Sonnet reviews (one shot): physics, visual, expert
  3. Executor applies combined feedback
  4. Haiku verifies with diff image → one more fix if needed

Usage as CLI:
  python feedback_loop.py "task description" /path/to/workdir
  python feedback_loop.py --review-only /path/to/workdir

Usage as library:
  from feedback_loop import review_plot
  result = review_plot(work_dir="/path/to/workdir")
  result = review_plot(work_dir="/path/to/workdir", task="Generate a Z mass plot...")
  result = review_plot(work_dir="/path/to/workdir",
                       task_context="Z→ll dilepton mass, template fit with 3 MC components")
"""

import subprocess
import json
import sys
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
SRC_DIR = SCRIPT_DIR / "src"

# Import diff tool
sys.path.insert(0, str(SRC_DIR))
from plot_diff import make_diff


# ── Load prompts from src/ ───────────────────────────────────────────

def load_prompt(name: str) -> str:
    return (SRC_DIR / name).read_text().strip()

MAXIMS_PATH = SRC_DIR / "plotting-maxims.md"
PLOTTING_MAXIMS = load_prompt("plotting-maxims.md")
EXECUTOR_INITIAL = load_prompt("executor-initial.md")
EXECUTOR_FIX = load_prompt("executor-fix.md")
HAIKU_CHECK = load_prompt("haiku-check.md").format(
    maxims_path=MAXIMS_PATH, script_path="{script_path}",
)
HAIKU_VERIFY = load_prompt("haiku-verify.md")
SONNET_PHYSICS = load_prompt("sonnet-physics.md")
SONNET_VISUAL = load_prompt("sonnet-visual.md").format(maxims_path=MAXIMS_PATH)
SONNET_EXPERT = load_prompt("sonnet-expert.md").format(maxims_path=MAXIMS_PATH)


# ── Agent calls ──────────────────────────────────────────────────────

def run_claude(prompt: str, model: str, tools: str = "Read,Write,Bash,Edit",
               timeout: int = 240, cwd: str = ".") -> dict:
    try:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--model", model,
             "--tools", tools,
             "--allowedTools", tools,
             "--permission-mode", "bypassPermissions",
             "--no-session-persistence",
             "--output-format", "json"],
            capture_output=True, text=True, timeout=timeout,
            cwd=cwd,
        )
        data = json.loads(result.stdout)
        return {
            "status": "ok",
            "output": data.get("result", ""),
            "cost": data.get("total_cost_usd", 0),
            "duration_ms": data.get("duration_ms", 0),
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "output": "", "cost": 0, "duration_ms": 0}
    except Exception as e:
        return {"status": "error", "output": str(e), "cost": 0, "duration_ms": 0}


def run_reviewer(prompt: str, model: str, plot_file: Path) -> dict:
    full = f"{prompt}\n\nRead the image at: {plot_file}"
    return run_claude(full, model, tools="Read")


def run_haiku_check(plot_file: Path, script_file: Path) -> dict:
    prompt = HAIKU_CHECK.format(script_path=script_file)
    full = f"{prompt}\n\nRead the image at: {plot_file}"
    return run_claude(full, "haiku", tools="Read")


def run_haiku_verify(plot_file: Path, script_file: Path, feedback: str,
                     diff_file: Path = None) -> dict:
    prompt = HAIKU_VERIFY.format(feedback=feedback)
    full = f"{prompt}\n\nRead the AFTER image at: {plot_file}\nRead the script at: {script_file}"
    if diff_file and diff_file.exists():
        full += (f"\n\nAlso read the DIFF image at: {diff_file}\n"
                 "This shows BEFORE | AFTER | DIFF (10x amplified pixel differences). "
                 "Bright areas in the DIFF panel show where changes were made. Black = unchanged.")
    return run_claude(full, "haiku", tools="Read")


def _executor_fix(plot_script, plot_file, feedback, work_dir):
    current_script = plot_script.read_text() if plot_script.exists() else "MISSING"
    return run_claude(
        EXECUTOR_FIX.format(
            script_path=plot_script, current_script=current_script,
            plot_path=plot_file, feedback=feedback, maxims=PLOTTING_MAXIMS,
        ),
        "sonnet", timeout=300, cwd=str(work_dir),
    )


# ── Core review function ─────────────────────────────────────────────

def review_plot(
    work_dir: str | Path,
    task: str = None,
    task_context: str = None,
    script_name: str = "make_plot.py",
    plot_name: str = "plot.png",
    quiet: bool = False,
) -> dict:
    """
    Review and polish a plot to publication quality.

    Args:
        work_dir: Directory containing the plot script and image.
        task: If provided, generate the initial plot from this description.
              If None, review the existing plot (review-only mode).
        task_context: Optional physics context passed to reviewers,
                      e.g. "Template fit of Z→ll with Z+jets, ttbar, diboson".
                      Helps the physics referee and expert give better feedback.
        script_name: Name of the plotting script in work_dir.
        plot_name: Name of the plot image in work_dir.
        quiet: If True, suppress stdout printing.

    Returns:
        dict with keys:
            passed: bool — did all reviewers accept (or verification pass)?
            physics_ok: bool — did the physics referee accept?
            analysis_issues: str — physics problems that need upstream fixes
                             (wrong fit, bad values, miscalibration, etc.)
                             Empty string if none. This is the key output for
                             the calling pipeline — it surfaces analysis bugs.
            iterations: int — number of executor fix rounds
            cost: float — total API cost in USD
            versions: list[Path] — paths to all plot versions (v0, v1, ...)
            final_plot: Path — path to the final plot image
            log: str — full log text
            reviews: dict — raw Sonnet review outputs keyed by name
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    plot_script = work_dir / script_name
    plot_file = work_dir / plot_name
    log_file = work_dir / "loop_log.md"

    log_lines = []
    total_cost = [0.0]
    iteration = [0]
    versions = []

    def log(msg):
        if not quiet:
            print(msg, flush=True)
        log_lines.append(msg)
        log_file.write_text("\n".join(log_lines))

    def save_version():
        dst = work_dir / f"plot_v{iteration[0]}.png"
        if plot_file.exists():
            shutil.copy(plot_file, dst)
            versions.append(dst)

    log(f"\n{'='*60}")
    log(f"PLOT FEEDBACK LOOP — {datetime.now().isoformat()}")
    log(f"{'='*60}\n")

    # ── Initial generation (if task provided) ────────────────────────
    if task is not None:
        log(f"Task: {task}\n")
        log("## INITIAL GENERATION\n")
        prompt = EXECUTOR_INITIAL.format(
            task=task, script_path=plot_script, plot_path=plot_file,
            maxims=PLOTTING_MAXIMS,
        )
        result = run_claude(prompt, "sonnet", timeout=300, cwd=str(work_dir))
        total_cost[0] += result["cost"]
        log(f"  Executor: ${result['cost']:.4f}, {result['duration_ms']/1000:.1f}s\n")
    else:
        log("Mode: review-only\n")

    if not plot_file.exists():
        log("  ERROR: Plot not generated / not found. Aborting.")
        return {
            "passed": False, "physics_ok": False, "analysis_issues": "",
            "iterations": 0, "cost": total_cost[0],
            "versions": [], "final_plot": None,
            "log": "\n".join(log_lines), "reviews": {},
        }

    save_version()  # v0

    # ── Stage 1: Haiku pre-check ─────────────────────────────────────
    log("## STAGE 1: HAIKU PRE-CHECK\n")
    log("  ### Haiku spec check")
    r_haiku = run_haiku_check(plot_file, plot_script)
    total_cost[0] += r_haiku["cost"]
    log(f"    ${r_haiku['cost']:.4f}, {r_haiku['duration_ms']/1000:.1f}s")
    log(f"    {r_haiku['output']}\n")

    if "FAIL" in r_haiku["output"].upper():
        log("    → has FAILs — fixing\n")
        fix = _executor_fix(
            plot_script, plot_file,
            f"SPEC COMPLIANCE CHECK (fix all FAILs):\n{r_haiku['output']}",
            work_dir,
        )
        total_cost[0] += fix["cost"]
        iteration[0] += 1
        save_version()
        log(f"    Fix: ${fix['cost']:.4f}, {fix['duration_ms']/1000:.1f}s\n")
    else:
        log("    → ALL PASS\n")

    # ── Stage 2: Sonnet reviews (one shot) ───────────────────────────
    log("## STAGE 2: SONNET REVIEWS (one shot)\n")

    # Optionally prepend task context to physics and expert prompts
    physics_prompt = SONNET_PHYSICS
    expert_prompt = SONNET_EXPERT
    if task_context:
        ctx = f"Context about this plot: {task_context}\n\n"
        physics_prompt = ctx + physics_prompt
        expert_prompt = ctx + expert_prompt

    with ProcessPoolExecutor(max_workers=3) as ex:
        f_physics = ex.submit(run_reviewer, physics_prompt, "sonnet", plot_file)
        f_visual = ex.submit(run_reviewer, SONNET_VISUAL, "sonnet", plot_file)
        f_expert = ex.submit(run_reviewer, expert_prompt, "sonnet", plot_file)

        r_physics = f_physics.result()
        r_visual = f_visual.result()
        r_expert = f_expert.result()

    reviews = {
        "physics": r_physics["output"],
        "visual": r_visual["output"],
        "expert": r_expert["output"],
    }

    for name, r in [("Physics", r_physics), ("Visual", r_visual), ("Expert", r_expert)]:
        total_cost[0] += r["cost"]
        log(f"  {name}: ${r['cost']:.4f}, {r['duration_ms']/1000:.1f}s")
        log(f"  {r['output']}\n")

    # Collect feedback — split physics into analysis issues vs plot issues
    plot_feedback = ""
    analysis_issues = ""

    # Parse physics verdict — look for verdict keywords in context
    phys_text = r_physics["output"]
    physics_verdict = ""
    verdicts = ["ACCEPT", "MINOR REVISION", "MAJOR REVISION", "REJECT"]
    for line in phys_text.split("\n"):
        # Strip markdown formatting: **Verdict: ACCEPT**, ### Verdict: ACCEPT, etc.
        clean = line.strip().replace("*", "").replace("#", "").strip()
        clean_upper = clean.upper()
        # Check for "Verdict: X" or "Verdict X" patterns
        if "VERDICT" in clean_upper:
            after_verdict = clean_upper.split("VERDICT")[-1].strip().lstrip(":").strip()
            for v in verdicts:
                if after_verdict.startswith(v):
                    physics_verdict = v
                    break
        # Check for bare verdict on its own line
        if not physics_verdict and clean_upper in verdicts:
            physics_verdict = clean_upper
        if physics_verdict:
            break

    physics_ok = physics_verdict == "ACCEPT"

    # Always extract sections regardless of verdict — analysis issues
    # can exist even when physics ACCEPTs (warnings, notes)
    def _extract_section(text, header, end_markers):
        """Extract text between a header and the next section marker."""
        upper = text.upper()
        if header.upper() not in upper:
            return ""
        idx_start = upper.index(header.upper()) + len(header)
        remaining = text[idx_start:]
        for marker in end_markers:
            if marker.upper() in remaining.upper():
                idx_end = remaining.upper().index(marker.upper())
                return remaining[:idx_end].strip().lstrip("#").strip()
        return remaining.strip().lstrip("#").strip()

    raw_analysis = _extract_section(phys_text, "ANALYSIS ISSUES",
                                     ["### PLOT ISSUES", "### Verdict", "## PLOT", "## Verdict"])
    raw_plot = _extract_section(phys_text, "PLOT ISSUES",
                                 ["### Verdict", "## Verdict"])

    # Clean analysis issues — many ways the model says "no issues":
    # "None.", "None. The physics is sound...", paragraph then "None." at the end
    def _is_none_section(text):
        """Check if a section is saying 'no issues' in various ways."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines:
            return True
        # First or last line is "None" / "None."
        for line in [lines[0], lines[-1]]:
            if line.rstrip(".").upper() == "NONE":
                return True
        # Entire section starts with "None"
        if text.strip().upper().startswith("NONE"):
            return True
        return False

    if raw_analysis and not _is_none_section(raw_analysis):
        analysis_issues = raw_analysis
    else:
        analysis_issues = ""

    # Route plot issues to executor (only if not "None")
    if raw_plot and not _is_none_section(raw_plot):
        plot_feedback += f"PHYSICS REFEREE (plot issues):\n{raw_plot}\n\n"

    # If physics didn't use the structured format, fall back to full text
    if not physics_ok and "ANALYSIS ISSUES" not in phys_text.upper():
        plot_feedback += f"PHYSICS REFEREE:\n{phys_text}\n\n"

    out = r_visual["output"].upper()
    visual_ok = "ACCEPT" in out and "NOT ACCEPT" not in out
    if not visual_ok:
        plot_feedback += f"VISUAL STYLE:\n{r_visual['output']}\n\n"

    out = r_expert["output"].upper()
    expert_ok = "ACCEPT" in out and "SUGGESTION" not in out
    if not expert_ok:
        plot_feedback += f"EXPERT PHYSICIST SUGGESTIONS:\n{r_expert['output']}\n\n"

    log(f"  Physics: {'✅ ACCEPT' if physics_ok else '❌'}")
    log(f"  Visual:  {'✅ ACCEPT' if visual_ok else '❌'}")
    log(f"  Expert:  {'✅ ACCEPT' if expert_ok else '💡 suggestions'}")

    if analysis_issues:
        log(f"\n  ⚠️  ANALYSIS ISSUES (for upstream):\n  {analysis_issues}\n")

    passed = False

    if physics_ok and visual_ok and expert_ok:
        log("\n  → ALL ACCEPT — done!\n")
        passed = True
    elif plot_feedback:
        # ── Stage 3: Apply fixes ─────────────────────────────────────
        log("\n## STAGE 3: APPLY SONNET FEEDBACK\n")
        fix = _executor_fix(plot_script, plot_file, plot_feedback, work_dir)
        total_cost[0] += fix["cost"]
        iteration[0] += 1
        save_version()
        log(f"  Fix: ${fix['cost']:.4f}, {fix['duration_ms']/1000:.1f}s\n")

        # ── Stage 4: Haiku verification ──────────────────────────────
        log("## STAGE 4: HAIKU VERIFICATION\n")

        # Generate diff image
        pre_fix_version = iteration[0] - 1
        pre_fix_path = work_dir / f"plot_v{pre_fix_version}.png"
        diff_path = work_dir / f"diff_v{pre_fix_version}_v{iteration[0]}.png"
        if pre_fix_path.exists() and plot_file.exists():
            stats = make_diff(str(pre_fix_path), str(plot_file), str(diff_path))
            log(f"  Diff: RMS={stats['rms']}, changed={stats['changed_pct']}%\n")
        else:
            diff_path = None

        log("  ### Checking feedback was implemented + no new breakage")
        r_verify = run_haiku_verify(plot_file, plot_script, plot_feedback, diff_path)
        total_cost[0] += r_verify["cost"]
        log(f"    ${r_verify['cost']:.4f}, {r_verify['duration_ms']/1000:.1f}s")
        log(f"    {r_verify['output']}\n")

        verify_out = r_verify["output"].upper()
        if "PASS" in verify_out and "MISSED" not in verify_out and "BROKEN" not in verify_out:
            log("  → Verified — DONE\n")
            passed = True
        else:
            log("  → Issues found — one more fix\n")
            fix = _executor_fix(
                plot_script, plot_file,
                f"VERIFICATION FAILED — fix these:\n{r_verify['output']}",
                work_dir,
            )
            total_cost[0] += fix["cost"]
            iteration[0] += 1
            save_version()
            log(f"    Fix: ${fix['cost']:.4f}, {fix['duration_ms']/1000:.1f}s\n")
            passed = True  # best effort after final fix

    # ── Summary ──────────────────────────────────────────────────────
    log(f"\n{'='*60}")
    log(f"DONE — {iteration[0]} iterations, ${total_cost[0]:.4f} total")
    log(f"{'='*60}\n")

    return {
        "passed": passed,
        "physics_ok": physics_ok,
        "analysis_issues": analysis_issues,
        "iterations": iteration[0],
        "cost": total_cost[0],
        "versions": versions,
        "final_plot": plot_file if plot_file.exists() else None,
        "log": "\n".join(log_lines),
        "reviews": reviews,
    }


# ── CLI entry point ──────────────────────────────────────────────────

def main():
    review_only = "--review-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--review-only"]

    if review_only:
        work_dir = args[0] if args else str(SCRIPT_DIR / "feedback_run")
        result = review_plot(work_dir=work_dir)
    else:
        task = args[0] if args else (
            "Plot the forward-backward charge asymmetry <Q_FB> vs cos(theta) "
            "for Z->qq events at sqrt(s) = 91.2 GeV. Generate mock data."
        )
        work_dir = args[1] if len(args) > 1 else str(SCRIPT_DIR / "feedback_run")
        result = review_plot(work_dir=work_dir, task=task)

    print(f"\nPassed: {result['passed']}")
    print(f"Cost: ${result['cost']:.4f}")
    print(f"Iterations: {result['iterations']}")


if __name__ == "__main__":
    main()
