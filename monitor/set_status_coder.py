#!/usr/bin/env python3
"""Helper para A1 atualizar o monitor do agente Coder.
Uso:
  set_status_coder.py <state> ["current task"] ["activity text"]
States: online | working | idle | offline
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SF = os.path.join(BASE, "status_coder.json")


def load():
    if os.path.exists(SF):
        try:
            return json.load(open(SF))
        except Exception:
            return {}
    return {}


def main():
    s = load()
    state = sys.argv[1] if len(sys.argv) > 1 else None
    if state:
        s["state"] = state
    if len(sys.argv) > 2:
        s["current_task"] = sys.argv[2]
    else:
        if state and state != "working":
            s["current_task"] = {"online": "disponível", "idle": "ocioso",
                                 "offline": "offline"}.get(state, "disponível")
    if len(sys.argv) > 3:
        act = s.setdefault("activity", [])
        act.insert(0, {"ts": time.time(), "text": " ".join(sys.argv[3:])})
        s["activity"] = act[:20]
    s["last_update"] = time.time()
    tmp = SF + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SF)
    print("coder status updated:", s.get("state"), "|", s.get("current_task"))


if __name__ == "__main__":
    main()
