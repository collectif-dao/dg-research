# At the top of the file after imports

import numba
import numpy as np

IS_NUMBA = False


def _update_actor_health_impl(
    health: np.ndarray,
    total_damage: np.ndarray,
    total_recovery: np.ndarray,
    recovery_time: np.ndarray,
    damage: np.ndarray,
    current_timestamp: int,
    mask: np.ndarray,
) -> np.ndarray:
    initial_health = health.copy()

    is_damage_positive = damage > 0
    is_damage_negative = damage < 0
    abs_damage = np.abs(damage)

    mask1 = mask & is_damage_positive & ((health - damage) < 0)
    damage[mask1] = health[mask1]

    mask2 = mask & is_damage_positive
    total_damage[mask2] += damage[mask2]
    health[mask2] -= damage[mask2]

    mask3 = mask & is_damage_negative & ((health + abs_damage) > 100)
    damage[mask3] = -(100 - health[mask3])

    mask4 = mask & is_damage_negative & (total_damage > 0)
    total_recovery[mask4] += abs_damage[mask4]
    recovery_time[mask4] = current_timestamp

    mask5 = mask & is_damage_negative
    health[mask5] += abs_damage[mask5]

    health[:] = np.maximum(0, np.minimum(100, health))
    total_recovery[:] = np.minimum(total_recovery, total_damage)

    return health != initial_health


_update_actor_health_vector = _update_actor_health_impl
_update_actor_health_numba = numba.jit(nopython=True, fastmath=True, cache=True)(_update_actor_health_impl)


def update_actor_health(*args, **kwargs) -> np.ndarray:
    if IS_NUMBA:
        return _update_actor_health_vector(*args, **kwargs)
    return _update_actor_health_numba(*args, **kwargs)
