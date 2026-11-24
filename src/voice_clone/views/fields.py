from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


def labeled_field(label: str, control: Widget, hint: str = "", kind: str = "") -> ComposeResult:
    parts: list[Widget] = [Label(label, classes="field-label"), control]
    if hint:
        parts.append(Static(hint, classes="hint"))
    yield Vertical(*parts, classes=f"field {kind}".strip())
