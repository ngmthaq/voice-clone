from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from voice_clone.ui.main_screen import MainScreen
from voice_clone.ui.train_screen import TrainScreen


class HomeScreen(Screen[None]):
    """The first screen: choose to change your voice or to train a new one."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="home"):
            yield Static("What do you want to do?", id="home-title")
            yield Button("Voice changer", id="open-changer", variant="primary")
            yield Static(
                "Change your voice in real time for Zoom, Discord and other apps.",
                classes="hint home-hint",
            )
            yield Button("Train a voice", id="open-train")
            yield Static(
                "Make a new voice from recordings of your own voice.",
                classes="hint home-hint",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#open-changer", Button).focus()

    @on(Button.Pressed, "#open-changer")
    def _open_changer(self) -> None:
        self.app.push_screen(MainScreen())

    @on(Button.Pressed, "#open-train")
    def _open_train(self) -> None:
        self.app.push_screen(TrainScreen())
