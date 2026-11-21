from pathlib import Path

from textual.app import App
from textual.binding import Binding

from voice_clone.ui import HomeScreen


class VoiceCloneApp(App[None]):
    CSS_PATH = Path(__file__).parent / "ui" / "app.tcss"
    TITLE = "voice-clone"
    BINDINGS = [Binding("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())
