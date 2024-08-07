import pytest
from hypothesis import given

from specs.lido import Lido
from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.utils import sample_stETH_total_supply
from specs.tests.withdrawals.withdrawal_queue_claims_test import base_share_rate
from specs.tests.withdrawals.withdrawal_queue_request_withdrawals_test import withdrawal_amounts_strategy
from specs.time_manager import TimeManager
from specs.withdrawals.nft import WithdrawalQueueERC721
from specs.withdrawals.withdrawal_queue import Address


@given(
    ethereum_address_strategy(),
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18),
    ethereum_address_strategy(),
)
def test_safeTransferFrom(queue_address, owner_address, withdrawal_amounts, address_to):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    successful_transfer: bool = False

    if owner_address != Address.ZERO:
        request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

        queue.finalize(request_ids[-1], total_stETH_amount, base_share_rate)

        for request_id in request_ids:
            if address_to != Address.ZERO:
                if owner_address == address_to:
                    with pytest.raises(ValueError, match="TransferToThemselves"):
                        queue.safeTransferFrom(owner_address, owner_address, address_to, request_id)

                else:
                    with pytest.raises(ValueError, match="TransferFromIncorrectOwner"):
                        queue.safeTransferFrom(owner_address, address_to, owner_address, request_id)

                    queue.safeTransferFrom(owner_address, owner_address, address_to, request_id)
                    successful_transfer = True

            else:
                with pytest.raises(ValueError, match="TransferToZeroAddress"):
                    queue.safeTransferFrom(owner_address, owner_address, address_to, request_id)

        if successful_transfer:
            assert queue.balanceOf(owner_address) == 0
            assert queue.balanceOf(address_to) == len(request_ids)


@given(
    ethereum_address_strategy(),
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18),
    ethereum_address_strategy(),
)
def test_approve_and_transfer(queue_address, owner_address, withdrawal_amounts, address_to):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    successful_transfer: bool = False

    if owner_address != Address.ZERO:
        request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

        for request_id in request_ids:
            if address_to != Address.ZERO and owner_address != address_to:
                with pytest.raises(ValueError, match="ApprovalToOwner"):
                    queue.approve(owner_address, owner_address, request_id)

                with pytest.raises(ValueError, match="NotOwnerOrApprovedForAll"):
                    queue.approve(address_to, address_to, request_id)

                queue.approve(owner_address, address_to, request_id)

                queue.safeTransferFrom(address_to, owner_address, address_to, request_id)
                successful_transfer = True

        if successful_transfer:
            assert queue.balanceOf(owner_address) == 0
            assert queue.balanceOf(address_to) == len(request_ids)


@given(
    ethereum_address_strategy(),
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18),
    ethereum_address_strategy(),
    ethereum_address_strategy(),
)
def test_approval_for_all_and_transfer(queue_address, owner_address, withdrawal_amounts, address_to, operator):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    successful_transfer: bool = False

    if owner_address != Address.ZERO:
        request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

        for request_id in request_ids:
            if address_to != Address.ZERO and owner_address != address_to and operator != Address.ZERO:
                if operator == owner_address:
                    with pytest.raises(ValueError, match="ApproveToCaller"):
                        queue.setApprovalForAll(owner_address, owner_address, True)
                else:
                    queue.setApprovalForAll(owner_address, operator, True)
                    queue.safeTransferFrom(operator, owner_address, address_to, request_id)
                    successful_transfer = True

        if successful_transfer:
            assert queue.balanceOf(owner_address) == 0
            assert queue.balanceOf(address_to) == len(request_ids)


@given(
    ethereum_address_strategy(),
    ethereum_address_strategy(),
    withdrawal_amounts_strategy(100, 1000 * 10**18),
    ethereum_address_strategy(),
)
def test_claimed_nft_transfer_fails(queue_address, owner_address, withdrawal_amounts, address_to):
    lido = Lido(total_shares=sample_stETH_total_supply, total_supply=sample_stETH_total_supply)
    lido.set_buffered_ether(sample_stETH_total_supply)
    time_manager = TimeManager()
    time_manager.initialize()

    total_stETH_amount: int = 0
    for amount in withdrawal_amounts:
        total_stETH_amount += amount

    queue = WithdrawalQueueERC721()
    queue.initialize(time_manager, lido, queue_address)
    queue.resume()

    hints: list[int] = []

    if owner_address != Address.ZERO:
        request_ids = queue.request_withdrawals(owner_address, withdrawal_amounts)

        queue.finalize(request_ids[-1], total_stETH_amount, 1 * 10**27)

        for _ in request_ids:
            hints.append(1)

        queue.claim_withdrawals(owner_address, request_ids, hints)

        for request_id in request_ids:
            if address_to != Address.ZERO and owner_address != address_to:
                with pytest.raises(ValueError, match="RequestAlreadyClaimed"):
                    queue.safeTransferFrom(owner_address, owner_address, address_to, request_id)

        assert queue.balanceOf(owner_address) == 0
