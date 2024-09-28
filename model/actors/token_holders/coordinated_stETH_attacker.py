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
from specs.dual_governance.proposals import ProposalStatus


@dataclass
class CoordinatedStETHAttackerActor(BaseActor):
    actor_type: ActorType = ActorType.CoordinatedAttacker
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def calculate_lock_amount(
        self, scenario: Scenario, dual_governance: DualGovernance, proposals: List[Proposal]
    ) -> Tuple[int, int]:
        if scenario is Scenario.VetoSignallingLoop:
            return self.calculate_veto_signalling_reaction(dual_governance, proposals)
        else:
            return 0, 0

    def attack_honest_actors(self, proposal: Proposal, stETH_gain_per_attacker: int, wstETH_gain_per_attacker: int):
        self.hypothetical_stETH_balance = self.st_eth_balance + stETH_gain_per_attacker
        self.hypothetical_wstETH_balance = self.wstETH_balance + wstETH_gain_per_attacker

    def calculate_veto_signalling_reaction(self, dual_governance: DualGovernance, proposals: List[Proposal]):
        for proposal in proposals:
            if proposal.proposal_type in [ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random]:
                if (
                    not dual_governance.timelock.proposals._is_proposal_marked_cancelled(proposal.id)
                    and (self.st_eth_locked == 0 and self.wstETH_locked == 0)
                    and dual_governance.timelock.get_proposal_status(proposal.id) is not ProposalStatus.Executed
                ):
                    return self.calculate_lock_into_escrow(dual_governance)

        if len(proposals) > 0:
            all_positive_proposals_executed = all(
                dual_governance.timelock.get_proposal_status(proposal.id) is ProposalStatus.Executed
                for proposal in proposals
                if proposal.proposal_type in [ProposalType.Positive, ProposalType.NoImpact, ProposalType.Random]
            )

            if all_positive_proposals_executed and (self.st_eth_locked > 0 or self.wstETH_locked > 0):
                return self.calculate_unlock_from_escrow(dual_governance)

        return 0, 0

    def calculate_lock_into_escrow(self, dual_governance: DualGovernance):
        first_proposal_timestamp = get_first_proposal_timestamp(dual_governance.timelock.proposals)
        if first_proposal_timestamp + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (self.st_eth_balance, self.wstETH_balance)

        return (0, 0)

    def calculate_unlock_from_escrow(self, dual_governance: DualGovernance):
        if self.recovery_time + self.reaction_delay < dual_governance.time_manager.get_current_timestamp():
            return (-self.st_eth_locked, -self.wstETH_locked)

        return (0, 0)
