from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from voice_clone.controllers import TrainController
from voice_clone.views.train_panel_widget import TrainPanelWidget

BACK_WHILE_TRAINING_MESSAGE = "Stop training first, then go back."


class TrainScreen(Screen[None]):
    SUB_TITLE = "Train a voice"
    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="panel"):
            with Vertical(classes="page"):
                yield Static(
                    "Make a new voice from 10–30 minutes of your recordings.", classes="intro"
                )
                yield TrainPanelWidget(id="train-panel")
        yield Footer()

    @property
    def controller(self) -> TrainController:
        return self.query_one("#train-panel", TrainPanelWidget).controller

    def action_back(self) -> None:
        panel = self.query_one("#train-panel", TrainPanelWidget)
        if panel.running:
            self.notify(BACK_WHILE_TRAINING_MESSAGE, severity="warning")
            return
        self.dismiss()
