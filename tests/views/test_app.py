import asyncio

import pytest
from textual.screen import Screen

from voice_clone.controllers import BusyReporter
from voice_clone.views.app import RESTART, VoiceCloneApp

BUSY = "Training is running."


class FakeController:
    def __init__(self, message: str | None) -> None:
        self.busy_message = message


class FakeScreen(Screen):
    def __init__(self, controller) -> None:
        super().__init__()
        self._controller = controller

    @property
    def controller(self):
        return self._controller


class ScreenWithoutController(Screen):
    pass


def _run(body):
    async def scenario():
        app = VoiceCloneApp()
        notes: list[str] = []
        app.notify = lambda message, **kwargs: notes.append(message)
        async with app.run_test() as pilot:
            await pilot.pause()
            result = await body(app, pilot, notes)
        return result, app

    return asyncio.run(scenario())


async def _push(app, pilot, screen):
    await app.push_screen(screen)
    await pilot.pause()


def test_fake_controller_is_a_busy_reporter():
    assert isinstance(FakeController(None), BusyReporter)


@pytest.mark.parametrize("key", ["q", "r"])
def test_idle_app_exits_on_first_press(key):
    async def body(app, pilot, notes):
        await pilot.press(key)
        await pilot.pause()
        return notes

    notes, app = _run(body)

    assert notes == []
    assert app.return_value == (RESTART if key == "r" else None)


@pytest.mark.parametrize("key", ["q", "r"])
def test_idle_pushed_screen_exits_on_first_press(key):
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController(None)))
        await pilot.press(key)
        await pilot.pause()
        return notes

    notes, app = _run(body)

    assert notes == []
    assert app.return_value == (RESTART if key == "r" else None)


@pytest.mark.parametrize(("key", "action"), [("q", "quit"), ("r", "restart")])
def test_busy_screen_needs_a_second_press(key, action):
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController(BUSY)))
        await pilot.press(key)
        await pilot.pause()
        after_first = (app.is_running, list(notes))
        await pilot.press(key)
        await pilot.pause()
        return after_first

    after_first, app = _run(body)

    assert after_first == (True, [f"{BUSY} Press {key} again to stop it and {action}."])
    assert app.return_value == (RESTART if key == "r" else None)


def test_a_different_key_does_not_confirm():
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController(BUSY)))
        await pilot.press("q")
        await pilot.press("r")
        await pilot.pause()
        still_running = app.is_running
        await pilot.press("r")
        await pilot.pause()
        return still_running, len(notes)

    (still_running, note_count), app = _run(body)

    assert still_running is True
    assert note_count == 2
    assert app.return_value == RESTART


def test_screen_without_controller_is_skipped():
    async def body(app, pilot, notes):
        await _push(app, pilot, ScreenWithoutController())
        return app._busy_message()

    message, _ = _run(body)

    assert message is None


def test_controller_that_is_not_a_busy_reporter_is_skipped():
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(object()))
        return app._busy_message()

    message, _ = _run(body)

    assert message is None


def test_top_busy_screen_message_wins():
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController("Lower is busy.")))
        await _push(app, pilot, FakeScreen(FakeController("Upper is busy.")))
        return app._busy_message()

    message, _ = _run(body)

    assert message == "Upper is busy."


def test_lower_busy_screen_is_found_when_top_is_idle():
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController("Lower is busy.")))
        await _push(app, pilot, FakeScreen(FakeController(None)))
        return app._busy_message()

    message, _ = _run(body)

    assert message == "Lower is busy."


def test_empty_message_counts_as_idle():
    async def body(app, pilot, notes):
        await _push(app, pilot, FakeScreen(FakeController("")))
        return app._busy_message()

    message, _ = _run(body)

    assert message is None
