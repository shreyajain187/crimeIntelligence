"""
Detects available compute backend (GPU/RAPIDS/CUDA vs CPU) and exposes a
single source of truth used across hotspot detection, classification, and
SHAP explanation. Never raises if GPU libraries are absent - always falls
back cleanly to the CPU stack so the project runs on an ordinary laptop.
"""
from dataclasses import dataclass, asdict
from functools import lru_cache


@dataclass
class BackendInfo:
    cuda_available: bool
    rapids_available: bool
    xgboost_cuda_available: bool
    gpu_name: str | None
    active_backend: str  # "gpu" or "cpu"

    def to_dict(self):
        return asdict(self)


@lru_cache(maxsize=1)
def detect_backend() -> BackendInfo:
    cuda_available = False
    gpu_name = None
    rapids_available = False
    xgboost_cuda_available = False

    try:
        import torch  # noqa: local, optional
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    if not cuda_available:
        # Fallback probe via nvidia-smi presence, without torch dependency.
        import shutil
        cuda_available = shutil.which("nvidia-smi") is not None

    try:
        import cudf  # noqa: F401
        import cuml  # noqa: F401
        rapids_available = True
    except Exception:
        rapids_available = False

    try:
        import xgboost as xgb
        # XGBoost >= 2.0 uses device="cuda"; presence of cupy/nvidia libs is
        # a reasonable proxy without actually training a model.
        xgboost_cuda_available = cuda_available
    except Exception:
        xgboost_cuda_available = False

    active_backend = "gpu" if (cuda_available and rapids_available) else "cpu"

    return BackendInfo(
        cuda_available=cuda_available,
        rapids_available=rapids_available,
        xgboost_cuda_available=xgboost_cuda_available,
        gpu_name=gpu_name,
        active_backend=active_backend,
    )
