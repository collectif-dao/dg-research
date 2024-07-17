import copy
from dataclasses import field


def default(obj):
    return field(default_factory=lambda: copy.copy(obj))


percent_base = 10**16
ether_base = 10**18
