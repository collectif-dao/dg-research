from enum import Enum


class ReactionTime(Enum):
    Normal = 1
    Quick = 2
    Slow = 3
    NoReaction = 4


class ModeledReactions(Enum):
    Normal = 1
    Accelerated = 2
    Slowed = 3
