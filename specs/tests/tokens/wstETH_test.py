import pytest
from hypothesis import assume, given

from specs.tests.accounting_test import ethereum_address_strategy
from specs.tests.tokens.ldo_test import token_amount_strategy
from specs.tokens.stETH import stETH_Token
from specs.tokens.wstETH import wstETH_Token
from specs.types.address import Address


@given(
    wst_eth_address=ethereum_address_strategy(),
    owner=ethereum_address_strategy(),
    amount=token_amount_strategy(),
)
def test_wrap_and_unwrap(wst_eth_address, owner, amount):
    assume(wst_eth_address != Address.ZERO and wst_eth_address != owner)
    stETH = stETH_Token()
    wstETH = wstETH_Token()

    wstETH.initialize(stETH, wst_eth_address)

    if owner != Address.ZERO and amount != 0:
        stETH._mint_shares(owner, amount)

        assert wstETH.balance_of(owner) == 0

        stETH.approve(owner, wst_eth_address, amount)
        wrapped = wstETH.wrap(owner, amount)

        assert wrapped == amount
        assert wstETH.balance_of(owner) == amount
        assert wstETH.get_total_supply() == amount
        assert stETH.balance_of(wst_eth_address) == amount
        assert stETH.balance_of(owner) == 0

        unwrapped = wstETH.unwrap(owner, wrapped)
        assert wrapped == unwrapped
        assert wstETH.balance_of(owner) == 0
        assert wstETH.get_total_supply() == 0
        assert stETH.balance_of(wst_eth_address) == 0
        assert stETH.balance_of(owner) == amount

    elif amount == 0:
        with pytest.raises(ValueError, match="ZeroAmount"):
            wstETH.wrap(owner, amount)
