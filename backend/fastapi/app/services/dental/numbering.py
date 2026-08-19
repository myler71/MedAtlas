# app/services/dental/numbering.py
"""Tooth numbering adapters: canonical FDI <-> Universal <-> Palmer.

Canonical form stored in DB is FDI (ISO 3950).
- Permanent teeth: quadrants 1-4, positions 1-8
  - FDI 11..18 (UR), 21..28 (UL), 31..38 (LL), 41..48 (LR)
- Primary teeth: quadrants 5-8, positions 1-5
  - FDI 51..55 (UR), 61..65 (UL), 71..75 (LL), 81..85 (LR)

Universal (ADA) numbers:
- Permanent: 1..32 (UR starts at 1 going clockwise to 32 at LR third molar)
- Primary: A..T

Palmer notation: quadrant symbol + position 1-8 (e.g. UR1)
"""

from typing import Optional

# Quadrant boundaries for Universal numbering (permanent)
_UNIVERSAL_QUADRANT_BOUNDS = {  # (start_inclusive, end_inclusive, fdi_quadrant)
    "UR": (1, 8, 1),
    "UL": (9, 16, 2),
    "LL": (17, 24, 3),
    "LR": (25, 32, 4),
}

_UNIVERSAL_PRIMARY_QUADRANT_BOUNDS = {
    "UR": ("A", "E", 5),
    "UL": ("F", "J", 6),
    "LL": ("K", "O", 7),
    "LR": ("P", "T", 8),
}


def fdi_to_universal(fdi: int) -> Optional[str]:
    """Convert FDI tooth number to Universal notation.

    Returns integer as string for permanent teeth, single letter for primary.
    Returns None if FDI is invalid.
    """
    if fdi < 11 or fdi > 85:
        return None
    fdi_quadrant = fdi // 10
    position = fdi % 10
    if fdi_quadrant in (1, 2, 3, 4):
        if not (1 <= position <= 8):
            return None
        # Universal is sequential 1..32 across quadrants clockwise from UR
        base = (fdi_quadrant - 1) * 8
        universal_num = base + position
        return str(universal_num)
    elif fdi_quadrant in (5, 6, 7, 8):
        if not (1 <= position <= 5):
            return None
        # Primary: UR=A-E, UL=F-J, LL=K-O, LR=P-T
        idx = (fdi_quadrant - 5) * 5 + (position - 1)
        return chr(ord("A") + idx)
    return None


def universal_to_fdi(universal: str) -> Optional[int]:
    """Convert Universal notation to FDI.

    Accepts integer 1..32 (permanent) or letter A..T (primary).
    """
    s = universal.strip().upper()
    if s.isdigit():
        n = int(s)
        if not (1 <= n <= 32):
            return None
        fdi_quadrant = ((n - 1) // 8) + 1
        position = ((n - 1) % 8) + 1
        return fdi_quadrant * 10 + position
    elif len(s) == 1 and "A" <= s <= "T":
        idx = ord(s) - ord("A")
        fdi_quadrant = (idx // 5) + 5
        position = (idx % 5) + 1
        return fdi_quadrant * 10 + position
    return None


def fdi_to_palmer(fdi: int) -> Optional[str]:
    """Convert FDI tooth number to Palmer notation.

    Palmer: quadrant symbol (UR┌, UL┐, LL└, LR┘) + position number 1-8.
    Returns None if FDI is invalid.
    """
    if fdi < 11 or fdi > 85:
        return None
    fdi_quadrant = fdi // 10
    position = fdi % 10
    is_primary = fdi_quadrant in (5, 6, 7, 8)
    max_position = 5 if is_primary else 8
    if not (1 <= position <= max_position):
        return None
    # Quadrant symbols (use unicode)
    symbols = {1: "┌", 2: "┐", 3: "└", 4: "┘",
               5: "┌ᵖ", 6: "┐ᵖ", 7: "└ᵖ", 8: "┘ᵖ"}
    return f"{symbols[fdi_quadrant]}{position}"


def palmer_to_fdi(palmer: str) -> Optional[int]:
    """Convert Palmer notation to FDI. Accepts ┌1..┘8 (and primary variants)."""
    s = palmer.strip()
    if len(s) < 2:
        return None
    sym = s[0]
    pos_str = s[1:].rstrip("ᵖ")
    if not pos_str.isdigit():
        return None
    position = int(pos_str)
    is_primary = "ᵖ" in s
    if is_primary:
        if not (1 <= position <= 5):
            return None
        sym_map = {"┌": 5, "┐": 6, "└": 7, "┘": 8}
    else:
        if not (1 <= position <= 8):
            return None
        sym_map = {"┌": 1, "┐": 2, "└": 3, "┘": 4}
    fdi_quadrant = sym_map.get(sym)
    if fdi_quadrant is None:
        return None
    return fdi_quadrant * 10 + position


def all_permanent_fdi() -> list[int]:
    return [q * 10 + p for q in (1, 2, 3, 4) for p in range(1, 9)]


def all_primary_fdi() -> list[int]:
    return [q * 10 + p for q in (5, 6, 7, 8) for p in range(1, 6)]
