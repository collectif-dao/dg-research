import pytest
from hypothesis import given

from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.tokens.ldo_test import token_amount_strategy
from specs.tokens.stETH import stETH_Token
from specs.withdrawals.withdrawal_queue import Address


@given(
    owner=ethereum_address_strategy(),
    to=ethereum_address_strategy(),
    amount=token_amount_strategy(min_value=1),
)
def test_transfer_workflow(owner, to, amount):
    token = stETH_Token()

    if owner != Address.ZERO:
        token._mint_shares(owner, amount)

        if owner != to:
            if to == Address.ZERO:
                with pytest.raises(ValueError, match="ZeroAddress"):
                    token.transfer(owner, to, amount)
            else:
                token.transfer(owner, to, amount)

                assert token.balance_of(owner) == 0
                assert token.shares_of(owner) == 0
                assert token.balance_of(to) == amount
                assert token.shares_of(to) == amount

                with pytest.raises(ValueError, match="NotEnoughBalance"):
                    token.transfer(owner, to, amount)

                token.transfer_shares(to, owner, amount)
                assert token.balance_of(to) == 0
                assert token.shares_of(to) == 0
                assert token.balance_of(owner) == amount
                assert token.shares_of(owner) == amount

                with pytest.raises(ValueError, match="ZeroAddress"):
                    token.transfer_shares(Address.ZERO, to, amount)

                token._burn_shares(owner, amount)

                with pytest.raises(ValueError, match="NotEnoughBalance"):
                    token._burn_shares(owner, amount)

                with pytest.raises(ValueError, match="ZeroAddress"):
                    token._burn_shares(Address.ZERO, amount)

    else:
        with pytest.raises(ValueError, match="ZeroAddress"):
            token._mint_shares(owner, amount)


@given(
    spender=ethereum_address_strategy(),
    owner=ethereum_address_strategy(),
    to=ethereum_address_strategy(),
    amount=token_amount_strategy(min_value=1),
)
def test_allowances(spender, owner, to, amount):
    token = stETH_Token()

    if owner != Address.ZERO and spender != Address.ZERO:
        token._mint_shares(owner, amount)

        if owner != to and owner != spender and to != Address.ZERO:
            assert token.balance_of(owner) == amount
            assert token.shares_of(owner) == amount
            assert token.balance_of(to) == 0
            assert token.shares_of(to) == 0

            token.approve(owner, spender, amount)

            assert token.allowance(owner, spender) == amount

            token.transfer_from(owner, spender, to, amount)

            assert token.allowance(owner, spender) == 0
            assert token.balance_of(owner) == 0
            assert token.shares_of(owner) == 0
            assert token.balance_of(to) == amount
            assert token.shares_of(to) == amount

            with pytest.raises(ValueError, match="AllowanceUnderflow"):
                token.decrease_allowance(owner, spender, amount)

            assert token.allowance(to, spender) == 0
            token.increase_allowance(to, spender, amount)
            assert token.allowance(to, spender) == amount

            token.transfer_from(to, spender, owner, amount)

    else:
        with pytest.raises(ValueError, match="ZeroAddress"):
            token.approve(owner, spender, amount)
