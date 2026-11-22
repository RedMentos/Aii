"""Pure UI-hierarchy helpers for the Android emulator lifecycle test."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET


def visible_labels(root: ET.Element) -> list[str]:
    return [
        value
        for node in root.iter("node")
        for value in (node.attrib.get("text", ""), node.attrib.get("content-desc", ""))
        if value
    ]


def button_center(root: ET.Element, label: str) -> tuple[int, int] | None:
    for node in root.iter("node"):
        node_label = node.attrib.get("text", "") or node.attrib.get("content-desc", "")
        if node_label.casefold() != label.casefold():
            continue
        if not node.attrib.get("class", "").endswith("Button"):
            continue
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
                             node.attrib.get("bounds", ""))
        if not match:
            continue
        x1, y1, x2, y2 = map(int, match.groups())
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def transient_overlay_action(root: ET.Element) -> str | None:
    labels = [value.casefold() for value in visible_labels(root)]
    if any("system ui isn't responding" in value for value in labels):
        return "Wait" if button_center(root, "Wait") is not None else "SYSTEM_UI_UNRESPONSIVE"
    if any("viewing full screen" in value for value in labels) and button_center(root, "GOT IT") is not None:
        return "GOT IT"
    return None
