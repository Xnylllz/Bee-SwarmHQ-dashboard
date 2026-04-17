from __future__ import annotations

import threading
from typing import Callable


try:
    import rumps
except Exception:  # pragma: no cover - optional dependency
    rumps = None


class MenuBarService:
    def __init__(self, on_show: Callable[[], None], on_quit: Callable[[], None]):
        self.on_show = on_show
        self.on_quit = on_quit
        self._app = None
        self._thread: threading.Thread | None = None

    @property
    def supported(self) -> bool:
        return rumps is not None

    def start(self) -> bool:
        if not self.supported or self._thread is not None:
            return self.supported
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def _run(self) -> None:
        if rumps is None:
            return

        class BeeMenuApp(rumps.App):
            def __init__(self, service: MenuBarService):
                super().__init__("Bee HQ")
                self.service = service
                self.menu = ["Show Dashboard", "Quit Bee HQ"]

            @rumps.clicked("Show Dashboard")
            def _show(self, _sender) -> None:
                self.service.on_show()

            @rumps.clicked("Quit Bee HQ")
            def _quit(self, _sender) -> None:
                self.service.on_quit()

        self._app = BeeMenuApp(self)
        self._app.run()

    def stop(self) -> None:
        if self._app is not None and rumps is not None:
            try:
                rumps.quit_application()
            except Exception:
                pass
