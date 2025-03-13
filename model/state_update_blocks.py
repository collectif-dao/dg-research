import model.parts.actors as actors
import model.parts.data_saving as data_saving
import model.parts.dg as dg
import model.parts.proposals as proposals
from model.parts import deposits, withdrawals
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
            "actors": actors.actor_cancel_proposals,
        },
    },
    {
        "label": "Proposal Scheduling and Execution",
        "policies": {"get_proposals_to_schedule_and_execute": proposals.get_proposals_to_schedule_and_execute},
        "variables": {
            "dual_governance": proposals.schedule_and_execute_proposals,
            "actors": actors.actor_execute_proposals,
        },
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
            "dual_governance": dg.update_dual_governance_state,
        },
    },
    {
        "label": "Process Withdrawals from Withdrawal Queue",
        "policies": {"calculate_withdrawal_amounts": dg.calculate_withdrawal_amounts_for_finalization_and_claims},
        "variables": {
            "dual_governance": dg.process_finalization_and_claims,
            "last_withdrawal_day": dg.update_last_withdrawal_day,
        },
    },
    {
        "label": "Track Rage Quit Escrows",
        "policies": {},
        "variables": {"rage_quit_escrows": withdrawals.track_rage_quit_escrow},
    },
    {
        "label": "Process ETH Withdrawals by Actors",
        "policies": {"eth_withdrawal_data": withdrawals.calculate_eth_withdrawals},
        "variables": {
            "actors": withdrawals.process_eth_withdrawals,
        },
    },
    {
        "label": "Process Deposits",
        "policies": {"calculate_deposit_amounts": deposits.calculate_deposit_amounts},
        "variables": {
            "dual_governance": deposits.process_deposits,
            "last_deposit_day": deposits.update_last_deposit_day,
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
