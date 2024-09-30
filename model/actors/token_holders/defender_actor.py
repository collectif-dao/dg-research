from dataclasses import dataclass, field
from typing import List, Tuple

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposal_type import ProposalType
from model.types.proposals import Proposal
from model.types.scenario import Scenario
from model.utils.proposals import get_first_proposal_timestamp
from specs.dual_governance import DualGovernance


@dataclass
class StETHDefenderActor(BaseActor):
    actor_type: ActorType = ActorType.SingleDefender
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def calculate_lock_amount(
        self, scenario: Scenario, dual_governance: DualGovernance, proposals: List[Proposal]
    ) -> Tuple[int, int]:
        for proposal in proposals:
            if proposal.proposal_type in [ProposalType.Negative, ProposalType.Danger, ProposalType.Hack]:
                if not dual_governance.timelock.proposals._is_proposal_marked_cancelled(proposal.id) and (
                    self.st_eth_locked == 0 and self.wstETH_locked == 0
                ):
                    return self.calculate_lock_into_escrow(dual_governance)

        if len(proposals) > 0:
            all_negative_proposals_canceled = all(
                dual_governance.timelock.proposals._is_proposal_marked_cancelled(proposal.id)
                for proposal in proposals
                if proposal.proposal_type in [ProposalType.Negative, ProposalType.Danger, ProposalType.Hack]
            )

            if all_negative_proposals_canceled and (self.st_eth_locked > 0 or self.wstETH_locked > 0):
                return self.calculate_unlock_from_escrow(dual_governance)

        return 0, 0

    # Internal calculations

    def calculate_lock_into_escrow(self, dual_governance: DualGovernance):
        first_proposal_timestamp = get_first_proposal_timestamp(dual_governance.timelock.proposals)
        if first_proposal_timestamp + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (self.st_eth_balance, self.wstETH_balance)

        return (0, 0)

    def calculate_unlock_from_escrow(self, dual_governance: DualGovernance):
        if self.recovery_time + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (-self.st_eth_locked, -self.wstETH_locked)

        return (0, 0)
