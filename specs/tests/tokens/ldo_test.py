import pytest
from hypothesis import given
from hypothesis import strategies as st

from specs.tests.accounting_test import ethereum_address_strategy
from specs.time_manager import TimeManager
from specs.tokens.ldo import LDO_Token
from specs.types.address import Address


def token_amount_strategy(min_value: int = 0, max_value: int = 1_000_000 * 10**18):
    return st.integers(min_value=min_value, max_value=max_value)


@given(
    sender=ethereum_address_strategy(),
    to=ethereum_address_strategy(),
    amount=token_amount_strategy(),
)
def test_transfer(sender, to, amount):
    time_manager = TimeManager()
    time_manager.initialize()

    token = LDO_Token()
    token.initialize(time_manager)

    if amount == 0:
        with pytest.raises(ValueError, match="ZeroAmount"):
            token.mint(sender, amount)
    else:
        token.mint(sender, amount)

        if sender != to:
            if to == Address.ZERO:
                with pytest.raises(ValueError, match="TransferToZeroAddress"):
                    token.transfer(sender, to, amount)
            else:
                token.transfer(sender, to, amount)

                assert token.balance_of(sender) == 0
                assert token.balance_of(to) == amount

                with pytest.raises(ValueError, match="NotEnoughBalance"):
                    token.transfer(sender, to, amount)

        elif sender == to and to != Address.ZERO:
            with pytest.raises(ValueError, match="TransferToThemselves"):
                token.transfer(sender, to, amount)


@given(
    owner=ethereum_address_strategy(),
    to=ethereum_address_strategy(),
    amount=token_amount_strategy(1),
)
def test_transfer_from(owner, to, amount):
    time_manager = TimeManager()
    time_manager.initialize()

    token = LDO_Token()
    token.initialize(time_manager)

    token.mint(owner, amount)
    token.approve(owner, to, amount)

    if owner != to:
        if to == Address.ZERO:
            with pytest.raises(ValueError, match="TransferToZeroAddress"):
                token.transfer_from(to, owner, to, amount)
        else:
            token.transfer_from(to, owner, to, amount)

            assert token.balance_of(owner) == 0
            assert token.balance_of(to) == amount

            with pytest.raises(ValueError, match="NotEnoughAllowance"):
                token.transfer_from(to, owner, to, amount)

    elif owner == to and to != Address.ZERO:
        with pytest.raises(ValueError, match="TransferToThemselves"):
            token.transfer_from(to, owner, to, amount)


@given(
    owner=ethereum_address_strategy(),
    to=ethereum_address_strategy(),
    amount=token_amount_strategy(),
)
def test_approve(owner, to, amount):
    time_manager = TimeManager()
    time_manager.initialize()

    token = LDO_Token()
    token.initialize(time_manager)

    token.approve(owner, to, amount)
    assert token.allowance(owner, to) == amount

    if amount != 0:
        with pytest.raises(ValueError, match="ApprovedAlready"):
            token.approve(owner, to, amount)


@given(
    owner=ethereum_address_strategy(),
    amount=token_amount_strategy(),
)
def test_mint(owner, amount):
    time_manager = TimeManager()
    time_manager.initialize()

    token = LDO_Token()
    token.initialize(time_manager)

    if amount == 0:
        with pytest.raises(ValueError, match="ZeroAmount"):
            token.mint(owner, amount)
    else:
        initial_supply = token.total_supply()
        token.mint(owner, amount)

        assert token.balance_of(owner) == amount
        assert token.total_supply() == initial_supply + amount


@given(
    owner=ethereum_address_strategy(),
    second_owner=ethereum_address_strategy(),
    amount=token_amount_strategy(1),
)
def test_burn(owner, second_owner, amount):
    time_manager = TimeManager()
    time_manager.initialize()

    token = LDO_Token()
    token.initialize(time_manager)

    if owner != second_owner:
        token.mint(owner, amount)
        initial_supply = token.total_supply()

        token.burn(owner, amount)
        assert token.balance_of(owner) == 0
        assert token.total_supply() == initial_supply - amount

        with pytest.raises(ValueError, match="NotEnoughTokensToBurnInTotalSupply"):
            token.burn(owner, amount)

        token.mint(second_owner, amount)

        with pytest.raises(ValueError, match="NotEnoughTokensToBurnInOwnerBalance"):
            token.burn(owner, amount)

    with pytest.raises(ValueError, match="ZeroAmount"):
        token.burn(owner, 0)
