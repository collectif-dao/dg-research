import numpy as np

from model.actors.actors import Actors
from specs.dual_governance import DualGovernance
from specs.escrow.escrow import Escrow
from specs.time_manager import TimeManager


def calculate_eth_withdrawals(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager: TimeManager = prev_state["time_manager"]

    # print("\n=== Calculate ETH Withdrawals ===")

    rage_quit_escrows: list[Escrow] = []
    if "rage_quit_escrows" in prev_state:
        rage_quit_escrows = prev_state["rage_quit_escrows"]

    if dual_governance.state.rage_quit_escrow is not None and (
        not rage_quit_escrows or dual_governance.state.rage_quit_escrow not in rage_quit_escrows
    ):
        rage_quit_escrows.append(dual_governance.state.rage_quit_escrow)

    if not rage_quit_escrows:
        # print("→ No rage quit escrows found")
        return {"eth_withdrawal_data": None}

    withdrawals_to_process = []

    for escrow in rage_quit_escrows:
        if not escrow.rage_quit_timelock_started_at.is_not_zero():
            # print("→ Rage quit timelock not started for escrow")
            continue

        withdrawals_timelock = escrow.rage_quit_extension_delay + escrow.rage_quit_withdrawals_timelock
        current_time = time_manager.get_current_timestamp_value()

        # print(f"Checking withdrawals for escrow {escrow.rage_quit_withdrawals_timelock.to_seconds()}")

        if current_time <= withdrawals_timelock + escrow.rage_quit_timelock_started_at:
            # print("→ Withdrawals timelock not passed for escrow")
            continue

        # print("→ Withdrawals timelock passed for escrow, can process ETH withdrawals")
        withdrawals_to_process.append(escrow)

    if not withdrawals_to_process:
        return {"eth_withdrawal_data": None}

    return {
        "eth_withdrawal_data": {"can_withdraw": True, "escrows": withdrawals_to_process, "current_time": current_time}
    }


def process_eth_withdrawals(params, substep, state_history, prev_state, policy_input):
    actors: Actors = prev_state["actors"]
    eth_withdrawal_data = policy_input["eth_withdrawal_data"]

    if eth_withdrawal_data is None or not eth_withdrawal_data["can_withdraw"]:
        return ("actors", actors)

    eth_withdrawals = np.zeros_like(actors.eth_balance)
    withdrawal_mask = np.zeros_like(actors.eth_balance, dtype=bool)

    for escrow in eth_withdrawal_data["escrows"]:
        locked_tokens_mask = (actors.stETH_locked > 0) | (actors.wstETH_locked > 0)
        locked_addresses = actors.address[locked_tokens_mask]

        for actor_address in locked_addresses:
            if actor_address in escrow.accounting.state.assets:
                if escrow.accounting.state.assets[actor_address].stETHLockedShares.to_uint256() > 0:
                    # print(
                    #     f"→ Found locked shares for {actor_address} in escrow {escrow.rage_quit_withdrawals_timelock.to_seconds()}"
                    # )
                    eth_value = escrow.withdraw_ETH(actor_address)

                    if eth_value.to_uint256() > 0:
                        actor_idx = np.where(actors.address == actor_address)[0][0]
                        eth_withdrawals[actor_idx] = eth_value.to_uint256()
                        withdrawal_mask[actor_idx] = True
                        # print(f"→ Withdrew {eth_value.to_uint256() / 10**18} ETH for {actor_address}")

    actors.register_eth_withdrawals(eth_withdrawals, withdrawal_mask)

    return ("actors", actors)


def track_rage_quit_escrow(params, substep, state_history, prev_state, policy_input):
    """Keep track of all rage quit escrows created during simulation"""
    dual_governance: DualGovernance = prev_state["dual_governance"]
    rage_quit_escrows = prev_state.get("rage_quit_escrows", [])

    if (
        dual_governance.state.rage_quit_escrow is not None
        and dual_governance.state.rage_quit_escrow not in rage_quit_escrows
    ):
        rage_quit_escrows.append(dual_governance.state.rage_quit_escrow)
        # print("→ Added new rage quit escrow to tracking")

    return ("rage_quit_escrows", rage_quit_escrows)
