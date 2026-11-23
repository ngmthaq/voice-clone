from pathlib import Path

from textual.app import App
from textual.binding import Binding

from voice_clone.ui import HomeScreen

RESTART = "restart"


class VoiceCloneApp(App[str]):
    CSS_PATH = Path(__file__).parent / "ui" / "app.tcss"
    TITLE = "voice-clone"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart", "Restart"),
    ]

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def action_restart(self) -> None:
        self.exit(RESTART)
