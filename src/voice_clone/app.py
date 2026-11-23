import time
from pathlib import Path

from textual.app import App
from textual.binding import Binding

from voice_clone.ui import HomeScreen

RESTART = "restart"
CONFIRM_SECONDS = 3.0


class VoiceCloneApp(App[str]):
    CSS_PATH = Path(__file__).parent / "ui" / "app.tcss"
    TITLE = "voice-clone"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart", "Restart"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._confirm: tuple[str, float] | None = None

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    async def action_quit(self) -> None:
        if self._confirmed("quit"):
            self.exit()

    def action_restart(self) -> None:
        if self._confirmed("restart"):
            self.exit(RESTART)

    def _confirmed(self, action: str) -> bool:
        """True when nothing is busy, or the same key was pressed again within a few seconds.

        Quitting while a screen is busy (training, installing, downloading, loading a voice)
        stops that work, so the first press only warns.
        """
        busy = self._busy_message()
        if busy is None:
            return True
        now = time.monotonic()
        if self._confirm is not None:
            last_action, pressed_at = self._confirm
            if last_action == action and now - pressed_at <= CONFIRM_SECONDS:
                self._confirm = None
                return True
        self._confirm = (action, now)
        self.notify(
            f"{busy} Press {action[0]} again to stop it and {action}.",
            severity="warning",
            timeout=CONFIRM_SECONDS,
        )
        return False

    def _busy_message(self) -> str | None:
        for screen in reversed(self.screen_stack):
            message = getattr(screen, "busy_message", None)
            if message:
                return str(message)
        return None
