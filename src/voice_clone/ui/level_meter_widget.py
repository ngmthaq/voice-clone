from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

BAR_WIDTH = 30
LEVEL_GAIN = 4.0


class LevelMeterWidget(Widget):
    level: reactive[float] = reactive(0.0)

    def __init__(self, label: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._label = label

    def render(self) -> Text:
        filled = round(min(1.0, max(0.0, self.level * LEVEL_GAIN)) * BAR_WIDTH)
        text = Text(f"{self._label:<8}")
        text.append("█" * filled, style="green")
        text.append("░" * (BAR_WIDTH - filled), style="grey37")
        return text
