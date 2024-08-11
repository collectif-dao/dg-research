from dataclasses import dataclass

from specs.time_manager import TimeManager
from specs.tokens.ldo import LDO_Token
from specs.tokens.stETH import stETH_Token
from specs.tokens.wstETH import wstETH_Token


@dataclass
class Lido(stETH_Token):
    wstETH: wstETH_Token = None
    ldo_token: LDO_Token = None
    time_manager: TimeManager = None

    buffered_ether: int = 0
    consensus_layer_ether: int = 0

    deposited_validators: int = 0
    consensus_layer_validators: int = 0

    deposit_size: int = 32 * 10**18  ## 32 ether

    def initialize(self, time_manager: TimeManager, wst_eth_address: str):
        self.time_manager = time_manager

        self.ldo = LDO_Token()
        self.ldo.initialize(time_manager)
        self.wstETH = wstETH_Token()
        self.wstETH.initialize(self, wst_eth_address)

    def transferShares(self, owner: str, new_owner: str, amount: int):
        self.transfer_shares(owner, new_owner, amount)

    def transferSharesFrom(self, owner: str, spender: str, new_owner: str, amount: int):
        self.transfer_from(owner, spender, new_owner, amount)

    def permit(self, address_from: str, address_to: str, value: int, deadline: int, v: int, r: str, s: str):
        pass

    def wstETH_permit(self, address_from: str, address_to: str, value: int, deadline: int, v: int, r: str, s: str):
        pass

    def get_shares_by_pooled_eth(self, eth_amount: int) -> int:
        return eth_amount * int(self.get_total_shares() / self.get_total_pooled_ether())

    def get_pooled_eth_by_shares(self, shares_amount: int) -> int:
        return shares_amount * int(self.get_total_pooled_ether() / self.get_total_shares())

    def get_total_supply(self) -> int:
        return self.get_total_pooled_ether()

    def get_total_pooled_ether(self) -> int:
        return self.get_buffered_ether() + self.get_cl_ether() + self._get_transient_balance()

    def get_buffered_ether(self) -> int:
        return self.buffered_ether

    def set_buffered_ether(self, buffered_eth: int):
        self.buffered_ether = buffered_eth

    def get_cl_ether(self) -> int:
        return self.consensus_layer_ether

    def set_cl_ether(self, cl_ether: int):
        self.consensus_layer_ether = cl_ether

    def _get_transient_balance(self) -> int:
        assert self.deposited_validators >= self.consensus_layer_validators

        return (self.deposited_validators - self.consensus_layer_validators) * self.deposit_size

    def wrap(self, sender: str, stETHAmount: int) -> int:
        return self.wstETH.wrap(sender, stETHAmount)

    def unwrap(self, sender: str, wstETHAmount: int) -> int:
        return self.wstETH.unwrap(sender, wstETHAmount)

    def wstETH_transfer(self, owner: str, new_owner: str, amount: int):
        self.wstETH.transfer(owner, new_owner, amount)

    def wstETH_transferFrom(self, owner: str, spender: str, new_owner: str, amount: int):
        self.wstETH.transfer_from(owner, spender, new_owner, amount)
