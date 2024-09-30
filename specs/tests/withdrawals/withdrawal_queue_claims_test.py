import pytest
from hypothesis import assume, given

from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.utils import sample_stETH_total_supply
from specs.tests.withdrawals.withdrawal_queue_request_withdrawals_test import withdrawal_amounts_strategy
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.withdrawals.errors import Errors
from specs.withdrawals.nft import WithdrawalQueueERC721
from specs.withdrawals.queue_base import Checkpoint

base_share_rate: int = 1 * 10**27


@given(ethereum_address_strategy(), ethereum_address_strategy(), withdrawal_amounts_strategy(100, 1000 * 10**18))
def test_finalize(queue_address, owner_address, withdrawal_amounts):
    assume(owner_address != Address.ZERO and queue_address != Address.ZERO and owner_address != queue_address)

    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    total_stETH_amount: int = 0
    total_shares_amount: int = 0

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    for amount in withdrawal_amounts:
        total_stETH_amount += amount
        total_shares_amount += lido.get_shares_by_pooled_eth(amount)

    lido._mint_shares(owner_address, total_shares_amount)
    lido.set_buffered_ether(lido.get_buffered_ether() + total_shares_amount)
    lido.approve(owner_address, queue_address, total_shares_amount)

    request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

    last_request_id = request_ids[-1]
    overflow_request_id = last_request_id + 1

    with pytest.raises(Errors.InvalidRequestId):
        queue.finalize(overflow_request_id, total_stETH_amount, base_share_rate)

    with pytest.raises(Errors.TooMuchEtherToFinalize):
        queue.finalize(last_request_id, (total_stETH_amount * 2), base_share_rate)

    queue.finalize(last_request_id, total_stETH_amount, base_share_rate)

    checkpoint: Checkpoint = queue.checkpoints[queue.get_last_checkpoint_index()]
    assert checkpoint.from_request_id == request_ids[0]
    assert checkpoint.max_share_rate == base_share_rate

    assert queue.get_last_finalized_request_id() == last_request_id
    assert queue.get_last_checkpoint_index() == 1
    assert queue.get_locked_ether_amount() == total_stETH_amount
    assert queue.find_checkpoint_hints([last_request_id], 1, queue.get_last_checkpoint_index())[0] == 1

    assert queue.balanceOf(owner_address) == len(withdrawal_amounts)


@given(ethereum_address_strategy(), ethereum_address_strategy(), withdrawal_amounts_strategy(100, 1000 * 10**18))
def test_claim_withdrawals(queue_address, owner_address, withdrawal_amounts):
    assume(owner_address != Address.ZERO and queue_address != Address.ZERO and owner_address != queue_address)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    total_stETH_amount: int = 0
    total_shares_amount: int = 0

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    for amount in withdrawal_amounts:
        total_stETH_amount += amount
        total_shares_amount += lido.get_shares_by_pooled_eth(amount)

    lido._mint_shares(owner_address, total_shares_amount)
    lido.set_buffered_ether(lido.get_buffered_ether() + total_shares_amount)
    lido.approve(owner_address, queue_address, total_shares_amount)

    request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

    request_id = request_ids[-1]
    hints: list[int] = []

    queue.finalize(request_id, total_stETH_amount, 1 * 10**27)

    for _ in request_ids:
        hints.append(1)

    assert queue.get_claimable_ether(request_ids, hints) == withdrawal_amounts

    if len(request_ids) > 1:
        with pytest.raises(Errors.ArraysLengthMismatch):
            queue.claim_withdrawals(owner_address, request_ids, [1])

    queue.claim_withdrawals(owner_address, request_ids, hints)

    assert queue.get_locked_ether_amount() == 0

    withdrawal_request_statuses = queue.get_withdrawal_status(request_ids)

    for withdrawal_request in withdrawal_request_statuses:
        assert withdrawal_request.is_claimed
        assert withdrawal_request.is_finalized

    assert queue.balanceOf(owner_address) == 0


@given(ethereum_address_strategy(), ethereum_address_strategy(), withdrawal_amounts_strategy(100, 1000 * 10**18))
def test_claim_withdrawals_to(queue_address, owner_address, withdrawal_amounts):
    assume(owner_address != Address.ZERO and queue_address != Address.ZERO and owner_address != queue_address)
    time_manager = TimeManager()
    time_manager.initialize()

    lido = Lido()
    lido.initialize(time_manager, Address.wstETH)
    lido._mint_shares(Address.DEAD, sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)

    total_stETH_amount: int = 0
    total_shares_amount: int = 0

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    for amount in withdrawal_amounts:
        total_stETH_amount += amount
        total_shares_amount += lido.get_shares_by_pooled_eth(amount)

    lido._mint_shares(owner_address, total_shares_amount)
    lido.set_buffered_ether(lido.get_buffered_ether() + total_shares_amount)
    lido.approve(owner_address, queue_address, total_shares_amount)

    request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

    request_id = request_ids[-1]
    hints: list[int] = []

    queue.finalize(request_id, total_stETH_amount, base_share_rate)

    for _ in request_ids:
        hints.append(1)

    assert queue.get_claimable_ether(request_ids, hints) == withdrawal_amounts

    if owner_address == Address.ZERO:
        with pytest.raises(Errors.ZeroRecipient):
            queue.claim_withdrawals_to(request_ids, hints, owner_address)
    else:
        if len(request_ids) > 1:
            with pytest.raises(Errors.ArraysLengthMismatch):
                queue.claim_withdrawals_to(request_ids, [1], owner_address)
        else:
            queue.claim_withdrawals_to(request_ids, hints, owner_address)

            assert queue.get_locked_ether_amount() == 0
            assert queue.balanceOf(owner_address) == 0

            withdrawal_request_statuses = queue.get_withdrawal_status(request_ids)

            for withdrawal_request in withdrawal_request_statuses:
                assert withdrawal_request.is_claimed
                assert withdrawal_request.is_finalized
