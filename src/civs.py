"""Civilization definitions for Stratagem v2."""
from __future__ import annotations

CIVS = {
    "ironborn": {
        "name": "Ironborn",
        "emoji": "⚒️",
        "desc": "Military units cost -1 iron",
        "unique_unit": "Huscarl",
        "unique_desc": "6 str, immune to archer type bonus",
    },
    "verdanti": {
        "name": "Verdanti",
        "emoji": "🌿",
        "desc": "+1 food from all provinces",
        "unique_unit": "Herbalist",
        "unique_desc": "Heals 1 unit per turn in province",
    },
    "tidecallers": {
        "name": "Tidecallers",
        "emoji": "🌊",
        "desc": "Trade routes yield +50% gold",
        "unique_unit": "Corsair",
        "unique_desc": "3 str, captures 1 gold per enemy killed",
    },
    "ashwalkers": {
        "name": "Ashwalkers",
        "emoji": "🔥",
        "desc": "Tech costs -25%",
        "unique_unit": "Sage",
        "unique_desc": "Province gets +1 all resources",
    },
}

def get_civ_info(civ_id: str) -> dict:
    return CIVS.get(civ_id, CIVS["ironborn"])
