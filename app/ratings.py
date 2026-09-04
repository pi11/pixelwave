from math import sqrt


def wilson_score(likes: int, dislikes: int, z: float = 1.96) -> float:
    """Return the lower bound of the Wilson score interval."""
    total = likes + dislikes
    if total == 0:
        return 0.0
    proportion = likes / total
    z_squared = z * z
    numerator = (
        proportion
        + z_squared / (2 * total)
        - z * sqrt((proportion * (1 - proportion) + z_squared / (4 * total)) / total)
    )
    return numerator / (1 + z_squared / total)
