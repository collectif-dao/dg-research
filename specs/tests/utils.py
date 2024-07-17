from escrow.escrow import Escrow
from utils import ether_base

test_escrow_address: str = "0x1234567890"
sample_stETH_total_supply: int = 1_000_000
sample_rage_quit_support: int = 3  # percent


def calc_rage_quit_support(escrow: Escrow):
    return (ether_base * (escrow.staked_stETH + escrow.finalized_ETH)) / (escrow.total_supply + escrow.finalized_ETH)
