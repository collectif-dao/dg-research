from dataclasses import dataclass


@dataclass
class Lido:
    total_supply: int
    total_shares: int

    buffered_ether: int = 0
    consensus_layer_ether: int = 0

    deposited_validators: int = 0
    consensus_layer_validators: int = 0

    deposit_size: int = 32 * 10**18  ## 32 ether

    def transferShares(self, new_owner, amount):
        pass
        # print(new_owner)
        # print(amount)

    def transferSharesFrom(self, owner, new_owner, amount):
        pass
        # print(owner)
        # print(new_owner)
        # print(amount)

    def get_shares_by_pooled_eth(self, eth_amount: int) -> int:
        return eth_amount * self.get_total_shares() / self.get_total_pooled_ether()

    def get_pooled_eth_by_shares(self, shares_amount: int) -> int:
        return shares_amount * self.get_total_pooled_ether() / self.get_total_shares()

    def get_total_supply(self) -> int:
        return self.total_supply

    def get_total_shares(self) -> int:
        return self.total_shares

    def _mint_shares(self, shares):
        self.total_shares += shares

    def _burn_shares(self, shares):
        self.total_shares -= shares

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
