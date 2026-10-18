#!/usr/bin/env python3
"""Shim de retrocompatibilidad histórica: redirige a scripts/monday.py."""
import os
import sys

ROOT = os.path.dirname(os.path.realpath(__file__))
MONDAY_SCRIPT = os.path.join(ROOT, "monday.py")
if not os.path.isfile(MONDAY_SCRIPT):
    print(f"error: no se encontró {MONDAY_SCRIPT}", file=sys.stderr)
    sys.exit(2)

print("warning: scripts/af.py is deprecated and will be removed in Monday v1.0.0; use scripts/monday.py", file=sys.stderr)
os.execv(sys.executable, [sys.executable, MONDAY_SCRIPT] + sys.argv[1:])
