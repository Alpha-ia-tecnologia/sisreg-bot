import time
import threading


class BotState:
    """Thread-safe singleton that tracks the bot's current progress."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.current_step = 0
        self.step_label = "Inicializando..."
        self.step_detail = ""
        self.logs: list[dict] = []
        self.records: list[dict] = []
        self.total_messages = 0
        self.sent_messages = 0
        self.failed_messages = 0
        self.finished = False
        self.screenshot: bytes | None = None
        self.message_status: dict[str, str] = {}  # codigo_solicitacao -> "sent" | "failed"
        self.running = False
        self.execution_id: int | None = None

    def reset(self):
        with self.lock:
            self.start_time = time.time()
            self.current_step = 0
            self.step_label = "Inicializando..."
            self.step_detail = ""
            self.logs.clear()
            self.records.clear()
            self.total_messages = 0
            self.sent_messages = 0
            self.failed_messages = 0
            self.finished = False
            self.screenshot = None
            self.message_status.clear()
            self.running = False
            self.execution_id = None

    def set_step(self, step: int, label: str, detail: str = ""):
        with self.lock:
            self.current_step = step
            self.step_label = label
            self.step_detail = detail
            self._add_log("step", f"Etapa {step}: {label}")

    def set_detail(self, detail: str):
        with self.lock:
            self.step_detail = detail

    def add_log(self, level: str, message: str):
        with self.lock:
            self._add_log(level, message)

    def _add_log(self, level: str, message: str):
        self.logs.append({
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        })

    def set_records(self, records: list[dict]):
        with self.lock:
            self.records = records

    def set_total_messages(self, total: int):
        with self.lock:
            self.total_messages = total

    def increment_sent(self, codigo: str = ""):
        with self.lock:
            self.sent_messages += 1
            if codigo:
                self.message_status[codigo] = "sent"

    def increment_failed(self, codigo: str = ""):
        with self.lock:
            self.failed_messages += 1
            if codigo:
                self.message_status[codigo] = "failed"

    def set_screenshot(self, data: bytes):
        with self.lock:
            self.screenshot = data

    def get_screenshot(self) -> bytes | None:
        with self.lock:
            return self.screenshot

    def set_running(self, value: bool):
        with self.lock:
            self.running = value

    def set_finished(self):
        with self.lock:
            self.finished = True
            self.running = False
            self._add_log("done", "Bot finalizado com sucesso")

    def to_dict(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return {
                "current_step": self.current_step,
                "step_label": self.step_label,
                "step_detail": self.step_detail,
                "logs": self.logs[-50:],
                "records": self.records,
                "total_messages": self.total_messages,
                "sent_messages": self.sent_messages,
                "failed_messages": self.failed_messages,
                "finished": self.finished,
                "elapsed": f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s",
                "message_status": dict(self.message_status),
                "running": self.running,
            }


state = BotState()
