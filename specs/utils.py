import copy
from dataclasses import field

from eth_account import Account


def default(obj):
    return field(default_factory=lambda: copy.copy(obj))


percent_base = 10**16
ether_base = 10**18


def generate_address():
    acc = Account.create()
    addr = acc.address
    return addr
