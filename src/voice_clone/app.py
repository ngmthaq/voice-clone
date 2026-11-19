from pathlib import Path

from textual.app import App
from textual.binding import Binding

from voice_clone.ui import MainScreen


class VoiceCloneApp(App[None]):
    CSS_PATH = Path(__file__).parent / "ui" / "app.tcss"
    TITLE = "voice-clone"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle", "Start/Stop"),
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def action_toggle(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.toggle()
