#!/usr/bin/env python3
"""
Scheduler setup for Sintetica Strategic Brain.

macOS:  generates and loads launchd plists
Linux:  prints systemd .service + .timer files (copy manually)

Usage:
    python .claude/scripts/scheduler_setup.py install     # create + load launchd plists
    python .claude/scripts/scheduler_setup.py uninstall   # unload + remove plists
    python .claude/scripts/scheduler_setup.py status      # show scheduler state
    python .claude/scripts/scheduler_setup.py systemd     # print Linux systemd units
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PYTHON = sys.executable

HEARTBEAT_LABEL = "com.sintetica.heartbeat"
REFLECTION_LABEL = "com.sintetica.reflection"

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = REPO_ROOT / ".claude" / "logs"

# COT = UTC-5.  Heartbeat: 7:00 AM – 8:00 PM COT every 30 min.
# launchd uses macOS system time — assumes system timezone is America/Bogota (COT).
# If your system runs UTC, pass --utc to print UTC-adjusted times.
HEARTBEAT_SLOTS_COT = [
    (h, m)
    for h in range(7, 21)
    for m in (0, 30)
]  # (7,0), (7,30), ..., (20,0) — 27 slots

REFLECTION_HOUR_COT = 8   # 8:00 AM COT


# ---------------------------------------------------------------------------
# Plist builder
# ---------------------------------------------------------------------------

def _interval_entry(hour: int, minute: int) -> str:
    return (
        "        <dict>\n"
        f"            <key>Hour</key><integer>{hour}</integer>\n"
        f"            <key>Minute</key><integer>{minute}</integer>\n"
        "        </dict>"
    )


def heartbeat_plist(utc: bool = False) -> str:
    slots = HEARTBEAT_SLOTS_COT
    if utc:
        # Shift COT → UTC (+5 hours)
        slots = [((h + 5) % 24, m) for (h, m) in slots]
    intervals = "\n".join(_interval_entry(h, m) for h, m in slots)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{HEARTBEAT_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON}</string>
        <string>{REPO_ROOT / ".claude" / "scripts" / "heartbeat.py"}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{REPO_ROOT}</string>

    <key>StartCalendarInterval</key>
    <array>
{intervals}
    </array>

    <key>StandardOutPath</key>
    <string>{LOG_DIR / "heartbeat.log"}</string>

    <key>StandardErrorPath</key>
    <string>{LOG_DIR / "heartbeat-error.log"}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""


def reflection_plist(utc: bool = False) -> str:
    hour = REFLECTION_HOUR_COT
    if utc:
        hour = (hour + 5) % 24  # 8 AM COT = 13:00 UTC
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{REFLECTION_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON}</string>
        <string>{REPO_ROOT / ".claude" / "scripts" / "memory_reflect.py"}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{REPO_ROOT}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>{hour}</integer>
        <key>Minute</key><integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{LOG_DIR / "reflection.log"}</string>

    <key>StandardErrorPath</key>
    <string>{LOG_DIR / "reflection-error.log"}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""


# ---------------------------------------------------------------------------
# systemd units (Linux / VPS)
# ---------------------------------------------------------------------------

SYSTEMD_HEARTBEAT_SERVICE = f"""[Unit]
Description=Sintetica Strategic Brain — Heartbeat
After=network.target

[Service]
Type=oneshot
ExecStart={PYTHON} {REPO_ROOT / ".claude" / "scripts" / "heartbeat.py"}
WorkingDirectory={REPO_ROOT}
StandardOutput=append:{LOG_DIR / "heartbeat.log"}
StandardError=append:{LOG_DIR / "heartbeat-error.log"}
"""

SYSTEMD_HEARTBEAT_TIMER = """[Unit]
Description=Sintetica Heartbeat — every 30 min, 12:00-01:00 UTC (7 AM-8 PM COT)

[Timer]
# COT = UTC-5.  Active 12:00-01:00 UTC = 7 AM-8 PM COT.
OnCalendar=*-*-* 12,12:30,13,13:30,14,14:30,15,15:30,16,16:30,17,17:30,18,18:30,19,19:30,20,20:30,21,21:30,22,22:30,23,23:30,00,00:30,01:00 UTC
Unit=sintetica-heartbeat.service
Persistent=false

[Install]
WantedBy=timers.target
"""

SYSTEMD_REFLECTION_SERVICE = f"""[Unit]
Description=Sintetica Strategic Brain — Daily Reflection
After=network.target

[Service]
Type=oneshot
ExecStart={PYTHON} {REPO_ROOT / ".claude" / "scripts" / "memory_reflect.py"}
WorkingDirectory={REPO_ROOT}
StandardOutput=append:{LOG_DIR / "reflection.log"}
StandardError=append:{LOG_DIR / "reflection-error.log"}
"""

SYSTEMD_REFLECTION_TIMER = """[Unit]
Description=Sintetica Reflection — daily 8 AM COT (13:00 UTC)

[Timer]
OnCalendar=*-*-* 13:00 UTC
Unit=sintetica-reflection.service
Persistent=true

[Install]
WantedBy=timers.target
"""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def require_macos():
    if platform.system() != "Darwin":
        print("Error: launchd commands require macOS. Use --systemd for Linux.", file=sys.stderr)
        sys.exit(1)


def install(utc: bool = False):
    require_macos()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    tz_note = "UTC-adjusted" if utc else "COT (assumes system timezone = America/Bogota)"
    print(f"Installing launchd plists with {tz_note} times…")

    plists = [
        (HEARTBEAT_LABEL, heartbeat_plist(utc)),
        (REFLECTION_LABEL, reflection_plist(utc)),
    ]

    for label, content in plists:
        plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"

        # Unload existing before overwriting
        if plist_path.exists():
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True,
            )

        plist_path.write_text(content)
        result = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  ✓ loaded {label}")
        else:
            print(f"  ✗ failed to load {label}: {result.stderr.strip()}")

    print("\nDone. Verify with: python .claude/scripts/scheduler_setup.py status")
    print(f"Logs: {LOG_DIR}/")


def uninstall():
    require_macos()
    for label in (HEARTBEAT_LABEL, REFLECTION_LABEL):
        plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            plist_path.unlink()
            print(f"  removed {label}")
        else:
            print(f"  not found: {label}")


def status():
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True,
        )
        lines = [
            ln for ln in result.stdout.splitlines()
            if "sintetica" in ln or "PID" in ln
        ]
        if lines:
            print("\n".join(lines))
        else:
            print("No sintetica jobs loaded. Run: python .claude/scripts/scheduler_setup.py install")

        # Show log tails
        for name, log in [("heartbeat", "heartbeat.log"), ("reflection", "reflection.log")]:
            log_path = LOG_DIR / log
            if log_path.exists():
                tail = log_path.read_text().splitlines()[-5:]
                print(f"\n-- {log} (last 5 lines) --")
                print("\n".join(tail))
    else:
        result = subprocess.run(
            ["systemctl", "--user", "list-timers", "--all"],
            capture_output=True, text=True,
        )
        lines = [ln for ln in result.stdout.splitlines() if "sintetica" in ln or "NEXT" in ln]
        print("\n".join(lines) if lines else "No sintetica timers active.")


def print_systemd():
    units = [
        ("sintetica-heartbeat.service", SYSTEMD_HEARTBEAT_SERVICE),
        ("sintetica-heartbeat.timer", SYSTEMD_HEARTBEAT_TIMER),
        ("sintetica-reflection.service", SYSTEMD_REFLECTION_SERVICE),
        ("sintetica-reflection.timer", SYSTEMD_REFLECTION_TIMER),
    ]
    print("# Copy each file to ~/.config/systemd/user/<filename>")
    print("# Then run: systemctl --user daemon-reload && systemctl --user enable --now sintetica-heartbeat.timer sintetica-reflection.timer\n")
    for filename, content in units:
        print(f"# ── {filename} ──")
        print(content)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sintetica scheduler setup")
    parser.add_argument(
        "command",
        choices=["install", "uninstall", "status", "systemd"],
        help="Action to perform",
    )
    parser.add_argument(
        "--utc",
        action="store_true",
        help="Use UTC-adjusted times in launchd plists (if macOS timezone is UTC, not COT)",
    )
    args = parser.parse_args()

    if args.command == "install":
        install(utc=args.utc)
    elif args.command == "uninstall":
        uninstall()
    elif args.command == "status":
        status()
    elif args.command == "systemd":
        print_systemd()
