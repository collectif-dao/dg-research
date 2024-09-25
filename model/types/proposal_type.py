from enum import Enum


class ProposalType(Enum):
    Positive = 1
    Negative = 2
    NoImpact = 3
    Danger = 4
    Random = 5
    Hack = 6


class ProposalSubType(Enum):
    NoEffect = 1
    FundsStealing = 2
    Bribing = 3
    Hack = 4


class ProposalGeneration(Enum):
    Random = 1
    TargetedAttack = 2
    NoGeneration = 3
