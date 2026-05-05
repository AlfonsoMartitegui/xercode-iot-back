from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


class VendorConfigError(Exception):
    pass


@lru_cache(maxsize=32)
def load_vendor_config(vendor: str) -> dict[str, object]:
    normalized_vendor = vendor.strip().lower()
    if not normalized_vendor:
        raise VendorConfigError("Vendor cannot be empty")

    config_path = _vendors_config_dir() / f"{normalized_vendor}.json"
    if not config_path.is_file():
        raise VendorConfigError(f"Vendor config not found vendor={normalized_vendor}")

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise VendorConfigError(f"Invalid vendor config JSON vendor={normalized_vendor}") from exc

    if not isinstance(config, dict):
        raise VendorConfigError(f"Vendor config must be an object vendor={normalized_vendor}")

    config_vendor = config.get("vendor")
    if config_vendor != normalized_vendor:
        raise VendorConfigError(
            f"Vendor config mismatch requested={normalized_vendor} configured={config_vendor}"
        )

    return config


def load_vendor_configs() -> list[dict[str, object]]:
    configs: list[dict[str, object]] = []
    for config_path in sorted(_vendors_config_dir().glob("*.json")):
        configs.append(load_vendor_config(config_path.stem))

    return configs


def _vendors_config_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "configs" / "vendors"
