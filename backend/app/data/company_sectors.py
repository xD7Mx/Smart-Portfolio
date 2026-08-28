"""
Symbol → Arabic sector name.

Kept as a thin, backward-compatible re-export: the real source of truth is
now app/data/saudi_directory.py (the single unified name+sector+logo file).
Every existing importer of SYMBOL_TO_SECTOR_AR keeps working unchanged.
"""

from app.data.saudi_directory import SYMBOL_TO_SECTOR_AR  # noqa: F401
