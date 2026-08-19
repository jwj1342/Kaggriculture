"""Batched Kaggriculture engine on PyTorch tensors (GPU-capable).

Replay recorded official episodes with `python -m rl.gpu.verify --suite`.
Submissions still run the official Python interpreter.
"""

from .env import KaggGpuEnv  # noqa: F401
from .state import Actions, TensorState  # noqa: F401
