from enum import Enum


class ActorType(Enum):
    BaseActor = 1
    HonestActor = 2
    SingleAttacker = 3
    CoordinatedAttacker = 4
    Hacker = 5
    SingleDefender = 6
    CoordinatedDefender = 7

def get_attacker_types() -> list[ActorType]:
    return [ActorType.SingleAttacker, ActorType.CoordinatedAttacker, ActorType.Hacker]

class ActorReaction(Enum):
    NoReaction = 0
    NoAction = 1
    Lock = 2
    Unlock = 3
    Quit = 4
