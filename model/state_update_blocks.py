from model.parts.data_saving import (
    save_data,
    write_data_fastparquet,
)
from model.parts.dg import (
    add_deltatime_to_dg,
    update_dg_time_manager,
    update_escrow,
)
from model.parts.proposals import (
    activate_attack,
    get_proposals_to_cancel,
    deactivate_attack,
    generate_proposal,
    initialize_proposals,
    register_proposals,
    schedule_and_execute_proposals,
    submit_proposals,
    cancel_proposals,
    get_proposals_to_schedule_and_execute
)
from model.utils.seed import initialize_seed

from .parts.actors import (
    actor_lock_or_unlock_in_escrow,
    actor_react_on_proposals,
    actor_reset_proposal_reaction,
    lock_or_unlock_stETH,
    actor_execute_proposals
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
            "dual_governance": submit_proposals,
            "proposals": register_proposals,
            "actors": actor_react_on_proposals,
            "is_active_attack": activate_attack,
            "non_initialized_proposals": initialize_proposals,
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
        "label": "Proposal Cancellation",
        "policies": {"cancel_all_pending_proposals": get_proposals_to_cancel},
        "variables": {
            "dual_governance": cancel_proposals,
            "is_active_attack": deactivate_attack,
            "actors": actor_reset_proposal_reaction,
        },
    },
    {
        "label": "Proposal Scheduling and Execution",
        "policies": {"get_proposals_to_schedule_and_execute": get_proposals_to_schedule_and_execute},
        "variables": {
            "dual_governance": schedule_and_execute_proposals,
            "actors": actor_execute_proposals
        }
    },
    {
        # data_saving.py
        "label": "Saving data",
        "policies": {"save_data": save_data},
        # "variables": {"common_dataframe": save_common_dataframe, "timestep_dataframe": save_timestep_dataframe},
        "variables": {
            "timestep_data": write_data_fastparquet,
        },
    },
]
