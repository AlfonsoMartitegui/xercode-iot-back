from __future__ import annotations


class ValueConversionError(Exception):
    pass


def convert_value(value: object, value_type: str, value_map: dict[str, object] | None = None) -> object:
    if value_map is not None:
        mapped_value = value_map.get(str(value).strip().lower())
        if mapped_value is not None:
            return mapped_value

    if value_type == "string":
        return str(value)

    if value_type == "float":
        return _float_value(value)

    if value_type == "int":
        return _int_value(value)

    if value_type == "boolean":
        return _boolean_value(value)

    raise ValueConversionError(f"Unsupported conversion type={value_type}")


def _float_value(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueConversionError(f"Value is not a float value={value}") from exc


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueConversionError(f"Value is not an integer value={value}") from exc


def _boolean_value(value: object) -> bool:
    if isinstance(value, bool):
        return value

    normalized_value = str(value).strip().lower()
    if normalized_value in {"true", "1", "yes", "on"}:
        return True
    if normalized_value in {"false", "0", "no", "off"}:
        return False

    raise ValueConversionError(f"Value is not a boolean value={value}")
