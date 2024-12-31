from datetime import date

import numpy as np

from model.actors.actors import Actors
from specs.dual_governance import DualGovernance
from specs.lido import Lido
from specs.time_manager import TimeManager


def calculate_deposit_amounts(params, substep, state_history, prev_state):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    time_manager: TimeManager = prev_state["time_manager"]
    deposit_cap: int = prev_state["deposit_cap"]
    actors: Actors = prev_state["actors"]
    last_deposit_day: date = prev_state["last_deposit_day"]
    process_deposits: bool = prev_state["process_deposits"]

    if not process_deposits:
        return {"deposit_data": None}

    current_day = time_manager.get_current_time().date()
    if last_deposit_day == current_day:
        return {"deposit_data": None}

    eth_balance_mask = actors.eth_balance > 0
    if not np.any(eth_balance_mask):
        return {"deposit_data": None}

    deposits_to_process = []
    total_to_deposit = 0

    for idx in np.where(eth_balance_mask)[0]:
        if total_to_deposit >= deposit_cap:
            # print(f"→ Reached daily deposit cap ({deposit_cap / 10**18} ETH)")
            break

        amount_to_deposit = min(actors.eth_balance[idx], deposit_cap - total_to_deposit)

        if amount_to_deposit <= 0:
            continue

        deposits_to_process.append({"actor_address": actors.address[idx], "amount": amount_to_deposit})
        total_to_deposit += amount_to_deposit
        # print(f"Added deposit: {actors.address[idx]}, amount {amount_to_deposit / 10**18} ETH")

    if deposits_to_process:
        dual_governance.last_deposit_day = current_day

    return {
        "deposit_data": {"deposits": deposits_to_process, "total_amount": total_to_deposit, "current_day": current_day}
    }


def process_deposits(params, substep, state_history, prev_state, policy_input):
    dual_governance: DualGovernance = prev_state["dual_governance"]
    lido: Lido = prev_state["lido"]
    actors: Actors = prev_state["actors"]
    deposit_data = policy_input["deposit_data"]

    if deposit_data is None:
        return ("dual_governance", dual_governance)

    # print(f"Processing {len(deposit_data['deposits'])} deposits")
    # print(f"Total amount to process: {deposit_data['total_amount'] / 10**18} ETH")

    deposit_amounts = np.zeros_like(actors.eth_balance)
    deposit_mask = np.zeros_like(actors.eth_balance, dtype=bool)

    for deposit in deposit_data["deposits"]:
        # print(f"Processing deposit: {deposit['actor_address']}, amount {deposit['amount'] / 10**18} ETH"
        actor_idx = np.where(actors.address == deposit["actor_address"])[0][0]
        deposit_amounts[actor_idx] = deposit["amount"]
        deposit_mask[actor_idx] = True

        buffered_ether = lido.get_buffered_ether()
        lido._mint_shares(deposit["actor_address"], deposit["amount"])
        lido.set_buffered_ether(buffered_ether + deposit["amount"])

    actors.process_deposits(deposit_amounts, deposit_mask)

    return ("dual_governance", dual_governance)


def update_last_deposit_day(params, substep, state_history, prev_state, policy_input):
    deposit_data = policy_input["deposit_data"]

    if deposit_data is None:
        return ("last_deposit_day", prev_state["last_deposit_day"])

    return ("last_deposit_day", deposit_data["current_day"])
