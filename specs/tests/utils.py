from specs.escrow.escrow import Escrow
from specs.utils import ether_base

test_escrow_address: str = "0x1234567890"
sample_stETH_total_supply: int = 1_000_000
sample_rage_quit_support: int = 3  # percent


def calc_rage_quit_support(escrow: Escrow):
    return (ether_base * (escrow.staked_stETH + escrow.finalized_ETH)) / (escrow.total_supply + escrow.finalized_ETH)


# unique_unstETHid = st.integers(min_value=0, max_value=1000).map(lambda x: x * 2).filter(lambda x: x % 3 != 0)
# unique_unstETHid2 = st.integers(min_value=0, max_value=1000).map(lambda x: x * 2).filter(lambda x: x % 3 != 0).unique()
