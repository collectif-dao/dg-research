import uuid


class Escrow:
    id: uuid.UUID
    staked: dict
    isRage: bool

    def __init__(self):
        self.id = uuid.uuid4()
        self.staked = {}
        self.isRage = False

    def GetTotalStaked(self) -> float:
        amount = 0
        for label, params in self.staked.items():
            amount = amount + params["amount"]
