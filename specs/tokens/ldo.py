from dataclasses import dataclass, field
from typing import Dict, List

from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.timestamp import Timestamp


@dataclass
class Checkpoint:
    from_timestamp: Timestamp
    value: int


@dataclass
class LDO_Token:
    name: str = "Lido DAO Token"
    decimals: int = 18
    symbol: str = "LDO"

    balances: Dict[str, List[Checkpoint]] = field(default_factory=dict)
    allowed: Dict[str, Dict[str, int]] = field(default_factory=dict)
    total_supply_history: List[Checkpoint] = field(default_factory=list)

    time_manager: TimeManager = None

    def initialize(self, time_manager: TimeManager):
        self.time_manager = time_manager

    ## ---
    ## transfers
    ## ---

    def transfer(self, sender: str, to: str, amount: int) -> bool:
        return self._transfer(sender, to, amount)

    def transfer_from(self, sender: str, _from: str, to: str, amount: int) -> bool:
        if self.allowed.get(_from, {}).get(sender, 0) < amount:
            raise ValueError("NotEnoughAllowance")

        self.allowed[_from][sender] -= amount
        return self._transfer(_from, to, amount)

    def _transfer(self, _from: str, to: str, amount: int) -> bool:
        if amount == 0:
            raise ValueError("ZeroAmount")

        if to == Address.ZERO:
            raise ValueError("TransferToZeroAddress")

        if to == _from:
            raise ValueError("TransferToThemselves")

        current_timestamp = self.time_manager.get_current_timestamp_value()

        previous_balance_from = self.balance_of_at(_from, current_timestamp)
        if previous_balance_from < amount:
            raise ValueError("NotEnoughBalance")

        self.update_value_at_now(self.balances.setdefault(_from, []), previous_balance_from - amount)
        previous_balance_to = self.balance_of_at(to, current_timestamp)
        assert previous_balance_to + amount >= previous_balance_to
        self.update_value_at_now(self.balances.setdefault(to, []), previous_balance_to + amount)

        return True

    ## ---
    ## allowances
    ## ---

    def approve(self, sender: str, spender: str, amount: int) -> bool:
        if amount != 0 and self.allowed.get(sender, {}).get(spender, 0) != 0:
            raise ValueError("ApprovedAlready")

        self.allowed.setdefault(sender, {})[spender] = amount
        return True

    def allowance(self, owner: str, spender: str) -> int:
        return self.allowed.get(owner, {}).get(spender, 0)

    ## ---
    ## balances and total supply
    ## ---

    def balance_of(self, owner: str) -> int:
        return self.balance_of_at(owner, self.time_manager.get_current_timestamp_value())

    def total_supply(self) -> int:
        return self.total_supply_at(self.time_manager.get_current_timestamp_value())

    def balance_of_at(self, owner: str, timestamp: Timestamp) -> int:
        return self.get_value_at(self.balances.get(owner, []), timestamp)

    def total_supply_at(self, timestamp: Timestamp) -> int:
        return self.get_value_at(self.total_supply_history, timestamp)

    ## ---
    ## mint/burn functions
    ## ---

    def mint(self, owner: str, amount: int) -> bool:
        if amount == 0:
            raise ValueError("ZeroAmount")

        curTotalSupply = self.total_supply()
        previous_balance_to = self.balance_of(owner)

        self.update_value_at_now(self.total_supply_history, curTotalSupply + amount)
        self.update_value_at_now(self.balances.setdefault(owner, []), previous_balance_to + amount)

        return True

    def burn(self, owner: str, amount: int) -> bool:
        if amount == 0:
            raise ValueError("ZeroAmount")

        curTotalSupply = self.total_supply()

        if curTotalSupply < amount:
            raise ValueError("NotEnoughTokensToBurnInTotalSupply")

        previous_balance_from = self.balance_of(owner)

        if previous_balance_from < amount:
            raise ValueError("NotEnoughTokensToBurnInOwnerBalance")

        self.update_value_at_now(self.total_supply_history, curTotalSupply - amount)
        self.update_value_at_now(self.balances.setdefault(owner, []), previous_balance_from - amount)

        return True

    ## ---
    ## internal methods
    ## ---

    def get_value_at(self, checkpoints: List[Checkpoint], timestamp: Timestamp) -> int:
        if not checkpoints:
            return 0

        if timestamp >= checkpoints[-1].from_timestamp:
            return checkpoints[-1].value
        if timestamp < checkpoints[0].from_timestamp:
            return 0

        min_idx = 0
        max_idx = len(checkpoints) - 1

        while max_idx > min_idx:
            mid = (max_idx + min_idx + 1) // 2
            if checkpoints[mid].from_timestamp <= timestamp:
                min_idx = mid
            else:
                max_idx = mid - 1

        return checkpoints[min_idx].value

    def update_value_at_now(self, checkpoints: List[Checkpoint], _value: int) -> None:
        current_timestamp = self.time_manager.get_current_timestamp_value()

        if not checkpoints or checkpoints[-1].from_timestamp < current_timestamp:
            checkpoints.append(Checkpoint(current_timestamp, _value))
        else:
            checkpoints[-1].value = _value
