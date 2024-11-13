from model.parts.data_saving import (
    save_common_dataframe_fastparquet,
    save_data,
    save_timestep_dataframe_fastparquet,
)
from model.parts.dg import (
    add_deltatime_to_dg,
    update_dg_time_manager,
    update_escrow,
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
from model.utils.seed import initialize_seed

from .parts.actors import (
    actor_lock_or_unlock_in_escrow,
    actor_react_on_proposal,
    actor_reset_proposal_reaction,
    lock_or_unlock_stETH,
)


def setup_seed(params, substep, state_history, prev_state):
    if prev_state["timestep"] == 0:
        initialize_seed(prev_state["seed"])
    return {}


state_update_blocks = [
    {
        "label": "Seed Initialization",
        "policies": {
            "initialize_seed": setup_seed,
        },
        "variables": {},
    },
    {
        # proposals.py
        "label": "Proposal Generation",
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
        "label": "Actors and Escrow",
        "policies": {"lock_or_unlock_stETH": lock_or_unlock_stETH},
        "variables": {"actors": actor_lock_or_unlock_in_escrow, "dual_governance": update_escrow},
    },
    {
        # dg.py
        "label": "Spec Timestep",
        "policies": {"add_deltatime_to_dg": add_deltatime_to_dg},
        "variables": {
            "dual_governance": update_dg_time_manager,
        },
    },
    {
        # proposals.py
        "label": "System Acts On Proposals",
        "policies": {"cancel_all_pending_proposals": cancel_all_pending_proposals},
        "variables": {
            "dual_governance": schedule_and_execute_proposals,
            "is_active_attack": deactivate_attack,
            "actors": actor_reset_proposal_reaction,
        },
    },
    {
        # data_saving.py
        "label": "Saving data",
        "policies": {"save_data": save_data},
        # "variables": {"common_dataframe": save_common_dataframe, "timestep_dataframe": save_timestep_dataframe},
        "variables": {
            "common_dataframe": save_common_dataframe_fastparquet,
            "timestep_dataframe": save_timestep_dataframe_fastparquet,
        },
    },
]
