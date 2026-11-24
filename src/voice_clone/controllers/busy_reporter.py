from typing import Protocol, runtime_checkable


@runtime_checkable
class BusyReporter(Protocol):
    @property
    def busy_message(self) -> str | None: ...
