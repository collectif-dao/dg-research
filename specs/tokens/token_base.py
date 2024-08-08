from dataclasses import dataclass, field
from typing import Dict

from specs.withdrawals.withdrawal_queue import Address


@dataclass
class TokenBase:
    name: str = "Token"
    symbol: str = "TKN"
    decimals: int = 18
    infinite_allowance: int = 2**256 - 1

    allowances: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def setup(self, name: str, symbol: str, decimals: int = 18):
        self.name = name
        self.symbol = symbol
        self.decimals = decimals

    def allowance(self, owner: str, spender: str) -> int:
        return self.allowances.get(owner, {}).get(spender, 0)

    def approve(self, owner: str, spender: str, amount: int):
        self._approve(owner, spender, amount)

    def _approve(self, owner: str, spender: str, amount: int) -> None:
        if owner == Address.ZERO or spender == Address.ZERO:
            raise ValueError("ZeroAddress")

        self.allowances.setdefault(owner, {})[spender] = amount

    def _spend_allowance(self, owner: str, spender: str, amount: int) -> None:
        allowance = self.allowance(owner, spender)

        if allowance != self.infinite_allowance:
            if allowance >= amount:
                self._approve(owner, spender, allowance - amount)
            else:
                raise ValueError("AllowanceExceeded")

    def _transfer(self, sender: str, recipient: str, amount: int, balances: Dict[str, int]):
        if sender == Address.ZERO or recipient == Address.ZERO:
            raise ValueError("ZeroAddress")

        balance = balances.get(sender, 0)

        if amount > balance:
            raise ValueError("NotEnoughBalance")

        balances[sender] = balance - amount
        balances[recipient] = balances.get(recipient, 0) + amount

    def _mint(self, recipient: str, amount: int, balances: Dict[str, int], total: int):
        if recipient == Address.ZERO:
            raise ValueError("ZeroAddress")

        if amount == 0:
            raise ValueError("ZeroAmount")

        balances[recipient] = balances.get(recipient, 0) + amount

        return total + amount

    def _burn(self, owner: str, amount: int, balances: Dict[str, int], total: int):
        if owner == Address.ZERO:
            raise ValueError("ZeroAddress")

        balance = balances.get(owner, 0)

        if amount > balance:
            raise ValueError("NotEnoughBalance")

        balances[owner] = balance - amount

        return total - amount
