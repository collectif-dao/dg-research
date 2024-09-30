from datetime import timedelta

from hypothesis import given
from hypothesis import strategies as st

from specs.committees.reseal_committee import ResealCommittee
from specs.dual_governance import DualGovernance
from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.committees.hash_consensus_test import hash_consensus_members_strategy
from specs.tests.utils import sample_stETH_total_supply, test_escrow_address
from specs.time_manager import TimeManager
from specs.types.address import Address


def sealables_strategy(min_size: int = 5):
    return st.lists(ethereum_address_strategy(), min_size=min_size, max_size=10, unique=True)


@given(
    members=hash_consensus_members_strategy(3),
    timelock_duration=st.integers(min_value=1, max_value=315500000),
    committee_address=ethereum_address_strategy(),
    sealables=sealables_strategy(),
)
def test_reseal_workflow(members, timelock_duration, committee_address, sealables):
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    dual_governance = DualGovernance()
    dual_governance.initialize(test_escrow_address, time_manager, lido)

    committee = ResealCommittee()
    committee.initialize(members, len(members), timelock_duration, time_manager, dual_governance, committee_address)

    for member in members:
        committee.vote_reseal(member, sealables, True)

    support, quorum, executed = committee.get_reseal_state(sealables)
    assert support == len(members)
    assert quorum == len(members)
    assert not executed

    time_manager.shift_current_time(timedelta(seconds=(timelock_duration + 1)))

    committee.execute_reseal(sealables)
