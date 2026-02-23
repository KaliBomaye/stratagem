"""Tech tree definitions for Stratagem v2."""
from __future__ import annotations
from .types import TechId, TECH_AGE, TECH_GROUPS, TECH_COST

TECH_INFO = {
    TechId.AGRICULTURE:    {"name": "Agriculture",    "desc": "+1 food from farms"},
    TechId.MINING:         {"name": "Mining",         "desc": "+1 iron from mines"},
    TechId.MASONRY:        {"name": "Masonry",        "desc": "Buildings complete instantly"},
    TechId.TACTICS:        {"name": "Tactics",        "desc": "All units +1 strength"},
    TechId.COMMERCE:       {"name": "Commerce",       "desc": "Markets produce +2 gold"},
    TechId.FORTIFICATION:  {"name": "Fortification",  "desc": "All provinces +1 defense"},
    TechId.BLITZ:          {"name": "Blitz",          "desc": "All units +1 speed"},
    TechId.SIEGE_CRAFT:    {"name": "Siege Craft",    "desc": "Siege units +3 vs fortifications"},
    TechId.DIPLOMACY_TECH: {"name": "Diplomacy",      "desc": "+2 gold/turn per active treaty"},
}

def can_research(player_age: int, player_techs: list[TechId], tech: TechId) -> bool:
    """Check if a tech can be researched."""
    if tech in player_techs:
        return False
    age = TECH_AGE[tech]
    if age > player_age:
        return False
    # Check if already picked a tech from this age group
    group = TECH_GROUPS[age]
    if any(t in player_techs for t in group):
        return False
    return True

def available_techs(player_age: int, player_techs: list[TechId]) -> list[TechId]:
    """Return list of techs available to research."""
    return [t for t in TechId if can_research(player_age, player_techs, t)]
