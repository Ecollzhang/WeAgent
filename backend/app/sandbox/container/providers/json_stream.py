from __future__ import annotations

import json


class JsonObjectStream:
    """Incrementally decode newline or pretty-printed JSON object streams."""

    def __init__(self) -> None:
        self.buffer = ""
        self.decoder = json.JSONDecoder()

    def feed(self, chunk: str, final: bool = False) -> tuple[list[dict], list[str]]:
        items = self.feed_items(chunk, final=final)
        events = [value for item_type, value in items if item_type == "event"]
        plain = [value for item_type, value in items if item_type == "plain"]
        return events, plain

    def feed_items(self, chunk: str, final: bool = False) -> list[tuple[str, object]]:
        self.buffer += chunk or ""
        items: list[tuple[str, object]] = []

        while self.buffer:
            stripped = self.buffer.lstrip()
            if stripped != self.buffer:
                self.buffer = stripped
            if not self.buffer:
                break

            if self.buffer[0] not in "[{":
                index = self._next_json_start(self.buffer)
                if index == -1:
                    if final or "\n" in self.buffer:
                        lines = self.buffer.splitlines()
                        if not final and not self.buffer.endswith(("\n", "\r")):
                            self.buffer = lines.pop() if lines else self.buffer
                        else:
                            self.buffer = ""
                        items.extend(
                            ("plain", line.strip())
                            for line in lines
                            if line.strip()
                        )
                    break
                prefix = self.buffer[:index]
                items.extend(
                    ("plain", line.strip())
                    for line in prefix.splitlines()
                    if line.strip()
                )
                self.buffer = self.buffer[index:]
                continue

            try:
                obj, index = self.decoder.raw_decode(self.buffer)
            except json.JSONDecodeError:
                if final:
                    items.extend(
                        ("plain", line.strip())
                        for line in self.buffer.splitlines()
                        if line.strip()
                    )
                    self.buffer = ""
                break

            self.buffer = self.buffer[index:]
            if isinstance(obj, dict):
                items.append(("event", obj))
            elif isinstance(obj, list):
                items.extend(("event", item) for item in obj if isinstance(item, dict))

        return items

    @staticmethod
    def _next_json_start(text: str) -> int:
        candidates = [idx for idx in (text.find("{"), text.find("[")) if idx >= 0]
        return min(candidates) if candidates else -1


def extract_text_value(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        candidates = [
            value.get("text"),
            value.get("content"),
            value.get("message"),
            value.get("delta"),
            value.get("summary"),
            value.get("output"),
            value.get("result"),
        ]
        for candidate in candidates:
            text = extract_text_value(candidate)
            if text:
                return text
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("message")
                    or item.get("delta")
                )
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part.strip() for part in parts if part and part.strip())
    return ""


def is_internal_plain_line(line: str) -> bool:
    text = (line or "").strip()
    lower = text.lower()
    if not text:
        return True
    return lower in {
        "reading additional input from stdin...",
        "outputting...",
        "输出中...",
    }
