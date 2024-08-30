from model.parts.dg import (
    add_deltatime_to_dg,
    update_dg_time_manager,
    update_escrow,
    update_lido_time_manager,
    update_time_manager,
)
from model.parts.proposals import (
    activate_attack,
    cancel_all_pending_proposals,
    deactivate_attack,
    generate_proposal,
    initialize_proposal,
    register_proposal,
    schedule_and_execute_proposals,
    submit_proposal,
)

from .parts.actors import (
    actor_lock_or_unlock_in_escrow,
    actor_react_on_proposal,
    actor_reset_proposal_reaction,
    lock_or_unlock_stETH,
)

state_update_blocks = [
    {
        # proposals.py
        "policies": {"generate_proposal": generate_proposal},
        "variables": {
            "dual_governance": submit_proposal,
            "proposals": register_proposal,
            "actors": actor_react_on_proposal,
            "is_active_attack": activate_attack,
            "non_initialized_proposals": initialize_proposal,
        },
    },
    {
        # agents.py, dg.py
        "policies": {"lock_or_unlock_stETH": lock_or_unlock_stETH},
        "variables": {"actors": actor_lock_or_unlock_in_escrow, "dual_governance": update_escrow},
    },
    {
        # dg.py
        "policies": {"add_deltatime_to_dg": add_deltatime_to_dg},
        "variables": {
            "time_manager": update_time_manager,
            "dual_governance": update_dg_time_manager,
            "lido": update_lido_time_manager,
        },
    },
    {
        # proposals.py
        "policies": {"cancel_all_pending_proposals": cancel_all_pending_proposals},
        "variables": {
            "dual_governance": schedule_and_execute_proposals,
            "is_active_attack": deactivate_attack,
            "actors": actor_reset_proposal_reaction,
        },
    },
]
