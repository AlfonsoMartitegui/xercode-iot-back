from __future__ import annotations


class NativeTopicPatternError(Exception):
    pass


def match_topic_pattern(
    topic: str,
    pattern: str,
    native_path_mode: str | None = None,
) -> dict[str, str] | None:
    topic_parts = topic.split("/")
    pattern_parts = pattern.split("/")
    values: dict[str, str] = {}

    topic_index = 0
    for pattern_index, pattern_part in enumerate(pattern_parts):
        if _is_placeholder(pattern_part):
            placeholder = pattern_part[1:-1]
            is_last_pattern_part = pattern_index == len(pattern_parts) - 1
            if native_path_mode == "rest" and placeholder == "native_path" and is_last_pattern_part:
                if topic_index >= len(topic_parts):
                    return None
                values[placeholder] = "/".join(topic_parts[topic_index:])
                return values

            if topic_index >= len(topic_parts):
                return None
            values[placeholder] = topic_parts[topic_index]
            topic_index += 1
            continue

        if topic_index >= len(topic_parts) or topic_parts[topic_index] != pattern_part:
            return None
        topic_index += 1

    if topic_index != len(topic_parts):
        return None

    return values


def _is_placeholder(value: str) -> bool:
    return value.startswith("{") and value.endswith("}") and len(value) > 2
