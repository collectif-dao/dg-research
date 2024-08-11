import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.utils import sample_stETH_total_supply
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.timestamp import Timestamps
from specs.withdrawals.errors import Errors
from specs.withdrawals.nft import WithdrawalQueueERC721
from specs.withdrawals.parameters import NFT_NAME, NFT_SYMBOL, WITHDRAWAL_QUEUE_BASE_URI
from specs.withdrawals.queue_base import WithdrawalRequest


def withdrawal_amounts_strategy(min_value: int = 1, max_value: int = 100_000 * 10**18):
    return st.lists(st.integers(min_value, max_value), min_size=1, unique=True)


@given(ethereum_address_strategy())
def test_initialization(queue_address):
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)

    assert queue.name == NFT_NAME
    assert queue.symbol == NFT_SYMBOL
    assert queue.baseURI == WITHDRAWAL_QUEUE_BASE_URI
    assert queue.address == queue_address


@given(ethereum_address_strategy(), ethereum_address_strategy(), withdrawal_amounts_strategy())
def test_request_withdrawals(queue_address, owner_address, withdrawal_amounts):
    assume(owner_address != Address.ZERO and queue_address != Address.ZERO and owner_address != queue_address)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)

    with pytest.raises(Exception, match="ResumedExpected"):
        queue.request_withdrawals(owner_address, withdrawal_amounts)

    queue.resume()

    min_withdrawal: bool = False
    max_withdrawal: bool = False
    total_stETH_amount: int = 0
    total_shares_amount: int = 0
    total_approve: int = 0
    request_ids: list[int] = []

    for amount in withdrawal_amounts:
        total_approve += lido.get_shares_by_pooled_eth(amount)

        if amount < queue.MIN_STETH_WITHDRAWAL_AMOUNT:
            min_withdrawal = True
        elif amount > queue.MAX_STETH_WITHDRAWAL_AMOUNT:
            max_withdrawal = True

    lido._mint_shares(owner_address, total_approve)
    lido.set_buffered_ether(lido.get_buffered_ether() + total_approve)
    lido.approve(owner_address, queue_address, total_approve)

    if min_withdrawal and not max_withdrawal:
        with pytest.raises(Errors.RequestAmountTooSmall):
            queue.request_withdrawals(owner_address, withdrawal_amounts)

    if max_withdrawal and not min_withdrawal:
        with pytest.raises(Errors.RequestAmountTooLarge):
            queue.request_withdrawals(owner_address, withdrawal_amounts)

    if not min_withdrawal and not max_withdrawal:
        request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

        withdrawal_requests = queue.get_withdrawal_requests(owner_address)
        assert request_ids == withdrawal_requests

        withdrawal_request_statuses = queue.get_withdrawal_status(request_ids)

        for i, amount in enumerate(withdrawal_amounts):
            total_stETH_amount += amount
            total_shares_amount += lido.get_shares_by_pooled_eth(amount)

            current_withdrawal_request_status = withdrawal_request_statuses[i]
            assert current_withdrawal_request_status.amount_of_stETH == amount
            assert current_withdrawal_request_status.amount_of_shares == lido.get_shares_by_pooled_eth(amount)
            assert not current_withdrawal_request_status.is_claimed
            assert not current_withdrawal_request_status.is_finalized
            assert current_withdrawal_request_status.owner == owner_address
            assert current_withdrawal_request_status.timestamp == time_manager.get_current_timestamp_value()

            withdrawal_request: WithdrawalRequest = queue.queue[request_ids[i]]
            assert withdrawal_request.cumulative_stETH == total_stETH_amount
            assert withdrawal_request.cumulative_shares == total_shares_amount
            assert withdrawal_request.report_timestamp == Timestamps.ZERO

        assert queue.balanceOf(owner_address) == len(withdrawal_amounts)


@given(ethereum_address_strategy(), ethereum_address_strategy(), withdrawal_amounts_strategy(100, 1000 * 10**18))
def test_request_withdrawals_wstETH(queue_address, owner_address, wstETH_withdrawal_amounts):
    assume(owner_address != Address.ZERO and queue_address != Address.ZERO and owner_address != queue_address)
    time_manager = TimeManager()
    time_manager.initialize()
    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    total_stETH_amount: int = 0
    total_shares_amount: int = 0
    total_approve: int = 0
    request_ids: list[int] = []

    for amount in wstETH_withdrawal_amounts:
        total_approve += lido.get_shares_by_pooled_eth(amount)

    lido._mint_shares(owner_address, total_approve)
    lido.set_buffered_ether(lido.get_buffered_ether() + total_approve)
    lido.approve(owner_address, Address.wstETH, total_approve)
    lido.wrap(owner_address, total_approve)
    lido.wstETH.approve(owner_address, queue_address, total_approve)

    request_ids = queue.request_withdrawals_wsteth(owner_address, wstETH_withdrawal_amounts)

    withdrawal_requests = queue.get_withdrawal_requests(owner_address)
    assert request_ids == withdrawal_requests

    withdrawal_request_statuses = queue.get_withdrawal_status(request_ids)

    for i, wstETH_amount in enumerate(wstETH_withdrawal_amounts):
        total_stETH_amount += wstETH_amount
        total_shares_amount += lido.get_shares_by_pooled_eth(wstETH_amount)

        current_withdrawal_request_status = withdrawal_request_statuses[i]
        assert current_withdrawal_request_status.amount_of_stETH == wstETH_amount
        assert current_withdrawal_request_status.amount_of_shares == lido.get_shares_by_pooled_eth(wstETH_amount)
        assert not current_withdrawal_request_status.is_claimed
        assert not current_withdrawal_request_status.is_finalized
        assert current_withdrawal_request_status.owner == owner_address
        assert current_withdrawal_request_status.timestamp == time_manager.get_current_timestamp_value()

        withdrawal_request: WithdrawalRequest = queue.queue[request_ids[i]]
        assert withdrawal_request.cumulative_stETH == total_stETH_amount
        assert withdrawal_request.cumulative_shares == total_shares_amount
        assert withdrawal_request.report_timestamp == Timestamps.ZERO

    assert queue.balanceOf(owner_address) == len(wstETH_withdrawal_amounts)
