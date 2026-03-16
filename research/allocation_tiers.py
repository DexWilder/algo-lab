"""FQL Allocation Tiers -- Relative sizing tier definitions.

These are relative allocation tiers, not hard contract sizes. The execution
layer maps tiers to actual position sizes based on account configuration.

Tier ordering: OFF < MICRO < REDUCED < BASE < BOOST < MAX_ALLOWED
"""

# Tier constants with numeric ordering
OFF = 0
MICRO = 1
REDUCED = 2
BASE = 3
BOOST = 4
MAX_ALLOWED = 5

TIER_NAMES = {
    OFF: "OFF",
    MICRO: "MICRO",
    REDUCED: "REDUCED",
    BASE: "BASE",
    BOOST: "BOOST",
    MAX_ALLOWED: "MAX_ALLOWED",
}

TIER_VALUES = {v: k for k, v in TIER_NAMES.items()}

# Controller action -> base allocation tier mapping
ACTION_TO_BASE_TIER = {
    "FULL_ON": BASE,
    "REDUCED_ON": REDUCED,
    "PROBATION": MICRO,
    "OFF": OFF,
    "DISABLE": OFF,
    "ARCHIVE_REVIEW": OFF,
}


def tier_name(tier):
    """Get the string name for a numeric tier."""
    return TIER_NAMES.get(tier, "UNKNOWN")


def tier_up(tier, steps=1):
    """Move tier toward MAX_ALLOWED, clamped."""
    return min(MAX_ALLOWED, tier + steps)


def tier_down(tier, steps=1):
    """Move tier toward OFF, clamped."""
    return max(OFF, tier - steps)


def clamp_tier(tier, floor=OFF, ceiling=MAX_ALLOWED):
    """Clamp tier between floor and ceiling."""
    return max(floor, min(ceiling, tier))
