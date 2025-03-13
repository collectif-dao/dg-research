from enum import Enum


class Scenario(Enum):
    HappyPath = 1
    SingleAttack = 2
    CoordinatedAttack = 3
    SmartContractHack = 4
    VetoSignallingLoop = 5
    ConstantVetoSignallingLoop = 6
    RageQuitLoop = 7
