import json
from typing import Optional

_broadcast_hook: Optional[callable] = None

def set_broadcast_hook(fn):
    global _broadcast_hook
    _broadcast_hook = fn

def _send(action: str, data: dict = None):
    if _broadcast_hook is None:
        raise RuntimeError("broadcast hook not set")
    _broadcast_hook({"action": action, "data": data or {}})

# 对外 API
def send_to_ai1(text: str):
    _send("add", {"char": "ai1", "text": text})

def send_to_ai2(text: str):
    _send("add", {"char": "ai2", "text": text})

def switch_single():
    _send("mode", {"v": "single"})

def switch_dual():
    _send("mode", {"v": "dual"})

def show_summary(text: str):
    _send("summary", {"text": text})

def clear_all():
    _send("clear", {})

def next_bubble():
    _send("next_bubble")