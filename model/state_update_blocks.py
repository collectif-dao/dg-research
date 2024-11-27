import model.parts.actors as actors
import model.parts.data_saving as data_saving
import model.parts.dg as dg
import model.parts.proposals as proposals
from model.utils.seed import initialize_seed


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
        "policies": {"generate_proposal": proposals.generate_proposal},
        "variables": {
            "dual_governance": proposals.submit_proposals,
            "proposals": proposals.register_proposals,
            "is_active_attack": proposals.activate_attack,
            "non_initialized_proposals": proposals.initialize_proposals,
            "actors": actors.actor_submit_proposals,
        },
    },
    {
        "label": "Proposal Cancellation",
        "policies": {"cancel_all_pending_proposals": proposals.get_proposals_to_cancel},
        "variables": {
            "dual_governance": proposals.cancel_proposals,
            "is_active_attack": proposals.deactivate_attack,
            "actors": actors.actor_cancel_proposals
        }
    },
    {
        "label": "Proposal Scheduling and Execution",
        "policies": {"get_proposals_to_schedule_and_execute": proposals.get_proposals_to_schedule_and_execute},
        "variables": {
            "dual_governance": proposals.schedule_and_execute_proposals,
            "actors": actors.actor_execute_proposals
        }
    },
    {
        # agents.py, dg.py
        "label": "Actors and Escrow",
        "policies": {"check_hp_and_calculate_reaction": actors.check_hp_and_calculate_reaction},
        "variables": {"actors": actors.react, "dual_governance": dg.update_escrow},
    },
    {
        # dg.py
        "label": "Spec Timestep",
        "policies": {"add_deltatime_to_dg": dg.add_deltatime_to_dg},
        "variables": {
            "dual_governance": dg.update_dg_time_manager,
        },
    },
    {
        # data_saving.py
        "label": "Saving data",
        "policies": {"save_data": data_saving.save_data},
        "variables": {
            "timestep_data": data_saving.write_data_fastparquet,
        },
    },
]