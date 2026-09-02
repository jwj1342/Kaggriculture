"""Pure regression tests for the Slurm profiling and submission helpers."""

import csv
import json
import os
import sys
import tempfile
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import slurm_audit as audit  # noqa: E402
import submit_rl             # noqa: E402
import submit_macro_audit    # noqa: E402
import submit_macro_rl       # noqa: E402
import run_preflight         # noqa: E402


def test_duration():
    assert audit.duration_seconds("00:01:30") == 90
    assert audit.duration_seconds("1-02:03:04") == 93784
    assert audit.duration_seconds("09:16.256") == 556.256
    assert audit.memory_mib("1048576K") == 1024
    assert audit.memory_mib("96G") == 98304


def test_gpu_csv():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "gpu.csv")
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["timestamp", "index", "name", "gpu_util_pct",
                             "memory_util_pct", "memory_used_mib",
                             "memory_total_mib", "power_w"])
            writer.writerow(["2026/08/24 00:00:00", 0, "H100", 0, 0, 100, 81000, 60])
            writer.writerow(["2026/08/24 00:00:02", 0, "H100", 100, 50, 40000, 81000, 500])
        report = audit.audit_gpu(path)
        assert report["samples"] == 2
        assert report["util_mean_pct"] == 50
        assert report["idle_samples_pct"] == 50
        assert report["memory_peak_mib"] == 40000


def test_timing_csv():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "timing.csv")
        fields = ["total_s", "wall_sps", "collect_s", "gae_s", "prepare_s",
                  "update_s", "metrics_s", "probe_s", "checkpoint_s"]
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerow(dict(total_s=10, wall_sps=100, collect_s=8,
                                 gae_s=0.5, prepare_s=0.1, update_s=1,
                                 metrics_s=0.1, probe_s=0, checkpoint_s=0.3))
        report = audit.audit_timing(path)
        assert report["iterations"] == 1
        assert report["phases"]["collect_s"]["pct"] == 80


def test_submit_chain():
    args = SimpleNamespace(backend="cpu", run="test", links=3,
                           pilot_minutes=5, full_minutes=25, min_sps=5000,
                           resume=False)
    jobs = submit_rl.build_jobs(args, ["--config", "rl/configs/granger.yaml"],
                                submit_rl.ROOT / "rl" / "runs" / "test",
                                expected_commit="abc123")
    assert jobs[0]["pilot"]
    assert "--time=00:10:00" in jobs[0]["command"]
    assert any("KG_EXPECT_COMMIT=abc123" in x for x in jobs[0]["command"])
    assert any("KG_RUN_MANIFEST=" in x for x in jobs[0]["command"])
    assert not any(x.startswith("--dependency") for x in jobs[0]["command"])
    assert "--dependency=afterok:JOB_1" in jobs[1]["command"]
    assert "--resume" in jobs[1]["command"]
    try:
        submit_rl._validate_train_args(["--device", "cuda"])
    except ValueError:
        pass
    else:
        raise AssertionError("managed device flag was accepted")
    changes = submit_rl._relevant_changes(
        " M docs/RUNS.md\n?? transcript.txt\n?? tools/new_tool.py")
    assert changes == [" M docs/RUNS.md", "?? tools/new_tool.py"]


def test_input_hash():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "input.npz")
        with open(path, "wb") as fh:
            fh.write(b"frozen-input")
        manifest = submit_rl._input_manifest(["--init-from", path])
        key = os.path.realpath(path)
        assert manifest[key]["sha256"] == run_preflight.sha256(path)
        manifest_path = os.path.join(tmp, "submission.json")
        with open(manifest_path, "w") as fh:
            json.dump({"source_dirty": True, "input_files": manifest}, fh)
        run_preflight.verify(manifest_path)
        with open(path, "ab") as fh:
            fh.write(b"changed")
        try:
            run_preflight.verify(manifest_path)
        except RuntimeError:
            pass
        else:
            raise AssertionError("changed input artifact was accepted")


def test_macro_audit_submit():
    defaults = submit_macro_audit.build_parser().parse_args([
        "--run", "defaults", "--hypothesis", "h", "--acceptance", "a",
        "--", "baseline", "--checkpoint", "model.pt"])
    assert defaults.mem_gb == 4
    args = SimpleNamespace(run="phase0", cpus=4, mem_gb=12, minutes=20)
    run_dir = submit_macro_audit.ROOT / "rl" / "runs" / "phase0"
    manifest = run_dir / "submission.json"
    command = submit_macro_audit.build_command(
        args, ["baseline", "--checkpoint", "model.pt"], run_dir, manifest)
    assert "--cpus-per-task=4" in command
    assert "--mem=12G" in command
    assert "--time=00:20:00" in command
    assert any(value == f"--export=ALL,KG_RUN_MANIFEST={manifest}"
               for value in command)
    assert command[-2:] == ["--output", str(run_dir / "result.json")]
    assert submit_macro_audit._validate_audit_args(
        ["--", "counterfactual", "--checkpoint", "model.pt"])[0] == "counterfactual"
    inputs = submit_macro_audit._audit_inputs([
        "counterfactual", "--option",
        "tape_prefix:agents/champ/k01.py:120",
        "--option=tape_prefix:agents/bench3/closer_cleo.py:24",
    ])
    assert "agents/champ/k01.py" in inputs
    assert "agents/bench3/closer_cleo.py" in inputs
    try:
        submit_macro_audit._validate_audit_args(["baseline", "--output=x.json"])
    except ValueError:
        pass
    else:
        raise AssertionError("managed output flag was accepted")


def test_macro_rl_submit():
    args = SimpleNamespace(
        run="macro-ppo", links=2, pilot_minutes=8, full_minutes=45,
        cpus=8, mem_gb=16, resume=False)
    run_dir = submit_macro_rl.ROOT / "rl" / "runs" / "macro-ppo"
    manifest = run_dir / "submission.json"
    jobs = submit_macro_rl.build_jobs(
        args, ["--B", "32", "--iters", "1000"], run_dir, manifest)
    assert "--time=00:13:00" in jobs[0]["command"]
    assert "--cpus-per-task=8" in jobs[0]["command"]
    assert "--dependency=afterok:JOB_1" in jobs[1]["command"]
    assert "--resume" in jobs[1]["command"]
    try:
        submit_macro_rl._validate_train_args(["--device=cpu"])
    except ValueError:
        pass
    else:
        raise AssertionError("managed macro device flag was accepted")


def test_preflight_ignores_prose_but_not_code():
    """A verdict written to docs/ must not invalidate a queued arm; code must.

    docs/RUNS.md is append-only by project discipline (CLAUDE.md requires a
    verdict per experiment), so an unrestricted `git diff <commit> --` put the
    run gate in direct conflict with the write-up step: on 2026-09-02 the
    9-link mkt-w2/mkt-w4/fut-w4 batch was already doomed to exit 42 with
    `docs/RUNS.md | 26 ++++` as the only difference. Everything executable
    stays gated -- that half is what makes a pre-registration binding.
    """
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *a: subprocess.run(a, cwd=tmp, check=True,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
        run("git", "init", "-q")
        run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        os.makedirs(os.path.join(tmp, "docs"))
        os.makedirs(os.path.join(tmp, "tools"))
        os.makedirs(os.path.join(tmp, "rl"))
        prose = os.path.join(tmp, "docs", "RUNS.md")
        queue = os.path.join(tmp, "rl", "TODO.md")
        code = os.path.join(tmp, "tools", "thing.py")
        with open(prose, "w") as fh:
            fh.write("# verdicts\n")
        with open(queue, "w") as fh:
            fh.write("# RL TODO\n")
        with open(code, "w") as fh:
            fh.write("X = 1\n")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "base")
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp,
                             capture_output=True, text=True).stdout.strip()

        manifest_path = os.path.join(tmp, "submission.json")
        with open(manifest_path, "w") as fh:
            json.dump({"commit": sha, "input_files": {}}, fh)

        saved = run_preflight.ROOT
        try:
            run_preflight.ROOT = tmp
            run_preflight.verify(manifest_path)          # clean tree passes

            with open(prose, "a") as fh:                 # a verdict is appended
                fh.write("\n## 2026-09-02 - a verdict\n")
            run_preflight.verify(manifest_path)          # must STILL pass

            # the live queue is markdown INSIDE the code tree, which the first
            # version of the exclusion list missed -- it voided 12 pending
            # links within the hour
            with open(queue, "a") as fh:
                fh.write("\n- a new standing row\n")
            run_preflight.verify(manifest_path)          # must STILL pass

            with open(code, "a") as fh:                  # code drifts
                fh.write("Y = 2\n")
            try:
                run_preflight.verify(manifest_path)
            except RuntimeError:
                pass
            else:
                raise AssertionError("a code change was accepted")
        finally:
            run_preflight.ROOT = saved


if __name__ == "__main__":
    test_duration()
    test_gpu_csv()
    test_timing_csv()
    test_submit_chain()
    test_input_hash()
    test_macro_audit_submit()
    test_macro_rl_submit()
    test_preflight_ignores_prose_but_not_code()
    print("infra tests passed")
