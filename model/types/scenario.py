from enum import Enum


class Scenario(Enum):
    HappyPath = 1
    SingleAttack = 2
    CoordinatedAttack = 3
    SmartContractHack = 4
    VetoSignallingLoop = 5
