# backend package init - minimal and import-safe for tests
# Keep side-effect free and UTF-8 text only.

__all__ = ["main", "models"]

def _try_import_main():
    try:
        from . import main as _m
        return _m
    except Exception:
        return None

def _try_import_models():
    try:
        from . import models as _models
        return _models
    except Exception:
        return None

_main = _try_import_main()
models = _try_import_models()

if _main is not None:
    if hasattr(_main, "get_ultra_beast_agent"):
        get_ultra_beast_agent = _main.get_ultra_beast_agent
    if hasattr(_main, "get_UltraBeastMainAgent"):
        get_UltraBeastMainAgent = _main.get_UltraBeastMainAgent

