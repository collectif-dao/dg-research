from dataclasses import dataclass, field
from typing import Dict

from specs.tokens.token_base import TokenBase


@dataclass
class stETH_Token(TokenBase):
    total_shares: int = 0
    shares: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        super().setup("Liquid Staked Ether 2.0", "stETH", 18)

    def get_total_shares(self) -> int:
        return self.total_shares

    def get_total_pooled_ether(self) -> int:
        return self.total_shares  ## test case only

    def balance_of(self, account: str) -> int:
        return self.get_pooled_eth_by_shares(self.shares.get(account, 0))

    def shares_of(self, account: str) -> int:
        return self.shares.get(account, 0)

    def get_shares_by_pooled_eth(self, eth_amount: int) -> int:
        return eth_amount * self.total_shares // self.get_total_pooled_ether()

    def get_pooled_eth_by_shares(self, shares_amount: int) -> int:
        return shares_amount * self.get_total_pooled_ether() // self.total_shares

    ## ---
    ## transfers
    ## ---

    def transfer(self, sender: str, recipient: str, amount: int):
        shares = self.get_shares_by_pooled_eth(amount)
        self._transfer(sender, recipient, shares, self.shares)

    def transfer_from(self, owner: str, spender: str, recipient: str, amount: int):
        self._spend_allowance(owner, spender, amount)
        shares = self.get_shares_by_pooled_eth(amount)
        self._transfer(owner, recipient, shares, self.shares)

    def transfer_shares(self, sender: str, recipient: str, shares: int) -> int:
        self._transfer(sender, recipient, shares, self.shares)
        tokens = self.get_pooled_eth_by_shares(shares)

        return tokens

    ## ---
    ## allowances
    ## ---

    def increase_allowance(self, owner: str, spender: str, added: int):
        self._approve(owner, spender, self.allowance(owner, spender) + added)

    def decrease_allowance(self, owner: str, spender: str, subtracted: int):
        allowance = self.allowance(owner, spender)

        if allowance < subtracted:
            raise ValueError("AllowanceUnderflow")

        self._approve(owner, spender, allowance - subtracted)

    ## ---
    ## mint/burn
    ## ---

    def _mint_shares(self, recipient: str, shares: int) -> int:
        self.total_shares = self._mint(recipient, shares, self.shares, self.total_shares)

        return self.total_shares

    def _burn_shares(self, account: str, shares: int) -> int:
        self.total_shares = self._burn(account, shares, self.shares, self.total_shares)

        return self.total_shares
