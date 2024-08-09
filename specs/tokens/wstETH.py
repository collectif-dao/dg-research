from dataclasses import dataclass, field
from typing import Dict

from specs.tokens.stETH import stETH_Token
from specs.tokens.token_base import TokenBase


@dataclass
class wstETH_Token(TokenBase):
    total_supply: int = 0
    balances: Dict[str, int] = field(default_factory=dict)
    stETH: stETH_Token = None
    address: str = ""

    def initialize(self, stETH: stETH_Token, wst_eth_address: str):
        super().setup("Wrapped liquid staked Ether 2.0", "wstETH", 18)
        self.stETH = stETH
        self.address = wst_eth_address

    def get_total_supply(self) -> int:
        return self.total_supply

    def balance_of(self, account: str) -> int:
        return self.balances.get(account, 0)

    ## ---
    ## wrap/unwrap
    ## ---

    def wrap(self, sender: str, amount: int) -> int:
        if amount == 0:
            raise ValueError("ZeroAmount")

        wstETH_amount = self.stETH.get_shares_by_pooled_eth(amount)
        self._mint(sender, wstETH_amount)
        self.stETH.transfer_from(sender, self.address, self.address, amount)

        return wstETH_amount

    def unwrap(self, sender: str, wstETH_amount: int) -> int:
        if wstETH_amount == 0:
            raise ValueError("ZeroAmount")

        stETH_amount = self.stETH.get_pooled_eth_by_shares(wstETH_amount)
        self._burn(sender, wstETH_amount)
        self.stETH.transfer(self.address, sender, stETH_amount)

        return stETH_amount

    ## ---
    ## transfers
    ## ---

    def transfer(self, sender: str, recipient: str, amount: int):
        self._transfer(sender, recipient, amount, self.balances)

    def transfer_from(self, owner: str, spender: str, recipient: str, amount: int):
        self._spend_allowance(owner, spender, amount)
        self._transfer(owner, recipient, amount, self.balances)

    ## ---
    ## mint/burn
    ## ---

    def _mint(self, recipient: str, amount: int):
        self.total_supply = super()._mint(recipient, amount, self.balances, self.total_supply)

    def _burn(self, owner: str, amount: int):
        self.total_supply = super()._burn(owner, amount, self.balances, self.total_supply)
