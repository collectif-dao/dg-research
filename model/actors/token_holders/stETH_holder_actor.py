from dataclasses import dataclass, field
from typing import List, Tuple

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposals import Proposal
from model.utils.proposals import get_first_proposal_timestamp
from specs.dual_governance import DualGovernance


@dataclass
class StETHHolderActor(BaseActor):
    actor_type: ActorType = ActorType.HonestActor
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def calculate_lock_amount(self, dual_governance: DualGovernance, proposals: List[Proposal]) -> Tuple[int, int]:
        return self.honest_health_based_reaction(dual_governance)

    # Personal implementation

    def honest_health_based_reaction(self, dual_governance: DualGovernance) -> Tuple[int, int]:
        if self.health > 0 and self.total_damage == 0 and self.total_recovery == 0:
            return (0, 0)
        elif self.health <= 0 and self.total_damage > 0:
            return self.calculate_lock_into_escrow(dual_governance)

        elif (
            self.total_recovery > 0
            and self.total_damage > 0
            and self.health > 0
            and (self.st_eth_locked > 0 or self.wstETH_locked > 0)
        ):
            return self.calculate_unlock_from_escrow(dual_governance)
        else:
            return (0, 0)

    # Internal calculations

    def calculate_lock_into_escrow(self, dual_governance: DualGovernance):
        first_proposal_timestamp = get_first_proposal_timestamp(dual_governance.timelock.proposals.state.proposals)
        if first_proposal_timestamp + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (self.st_eth_balance, self.wstETH_balance)

        return (0, 0)

    def calculate_unlock_from_escrow(self, dual_governance: DualGovernance):
        if self.last_locked_tx_timestamp + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (-self.st_eth_locked, -self.wstETH_locked)

        return (0, 0)
