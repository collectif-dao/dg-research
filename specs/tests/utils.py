from specs.escrow.escrow import Escrow
from specs.utils import ether_base

test_escrow_address: str = "0x1234567890"
sample_stETH_total_supply: int = 1_000_000 * ether_base
sample_rage_quit_support: int = 3  # percent


def calc_rage_quit_support(escrow: Escrow):
    finalized_ETH = escrow.accounting.state.unstETHTotals.finalizedETH
    unfinalized_shares = (
        escrow.accounting.state.stETHTotals.lockedShares + escrow.accounting.state.unstETHTotals.unfinalizedShares
    )
    left = escrow.lido.get_pooled_eth_by_shares(unfinalized_shares.value) + finalized_ETH.value
    right = escrow.lido.get_total_supply() + finalized_ETH.value

    return ether_base * left / right
