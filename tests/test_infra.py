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
    try:
        submit_macro_audit._validate_audit_args(["baseline", "--output=x.json"])
    except ValueError:
        pass
    else:
        raise AssertionError("managed output flag was accepted")


if __name__ == "__main__":
    test_duration()
    test_gpu_csv()
    test_timing_csv()
    test_submit_chain()
    test_input_hash()
    test_macro_audit_submit()
    print("infra tests passed")
