"""ridewme edge daemon — the decision engine (L0-L7) + crash fusion.

All camera CV, all drowsiness decisions, and all crash fusion happen here.
The daemon emits *signed events only*; video and raw sensors never leave it.
See CONTRACT.md (repo root) for the event schema and the golden flow.
"""

__version__ = "0.1.0"
