import copy
from dataclasses import field

from eth_account import Account


def default(obj):
    return field(default_factory=lambda: copy.copy(obj))


ether_base = 10**18
percent_base = ether_base // 100


def generate_address():
    acc = Account.create()
    addr = acc.address
    return addr
