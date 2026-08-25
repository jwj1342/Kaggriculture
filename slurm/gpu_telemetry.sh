#!/bin/bash
# Source after setup_env.sh. The caller must define PROJECT.

start_gpu_telemetry() {
    local run_id=${1:-adhoc}
    local profile_dir="$PROJECT/logs/profiles/$run_id"
    GPU_CSV="$profile_dir/${SLURM_JOB_ID:-local}-gpu.csv"
    GPU_TELEMETRY_PID=""
    mkdir -p "$profile_dir"
    echo "timestamp,index,name,gpu_util_pct,memory_util_pct,memory_used_mib,memory_total_mib,power_w" > "$GPU_CSV"
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw \
            --format=csv,noheader,nounits --loop=2 >> "$GPU_CSV" &
        GPU_TELEMETRY_PID=$!
    else
        echo "GPU-TELEMETRY warning=nvidia-smi-not-found"
    fi
}

stop_gpu_telemetry() {
    if [ -n "${GPU_TELEMETRY_PID:-}" ]; then
        kill "$GPU_TELEMETRY_PID" 2>/dev/null || true
        wait "$GPU_TELEMETRY_PID" 2>/dev/null || true
        GPU_TELEMETRY_PID=""
    fi
}

finish_gpu_telemetry() {
    stop_gpu_telemetry
    if [ -n "${GPU_CSV:-}" ] && [ "$(wc -l < "$GPU_CSV")" -gt 1 ]; then
        python "$PROJECT/tools/slurm_audit.py" --gpu "$GPU_CSV" || true
    fi
}
