from dataclasses import dataclass, field
from typing import List, Set

from model.types.proposal_type import ProposalSubType, ProposalType
from model.types.scenario import Scenario
from model.utils.proposals import determine_proposal_damage, determine_proposal_subtype, determine_proposal_type


@dataclass
class Proposal:
    id: int = 0
    timestep: int = 0
    damage: int = 0
    proposer: str = field(default_factory=lambda: "")
    proposal_type: ProposalType = field(default_factory=lambda: ProposalType.NoImpact)
    sub_type: ProposalSubType = field(default_factory=lambda: ProposalSubType.NoEffect)
    attack_targets: Set[str] = field(default_factory=lambda: set())
    cancelable: bool = True


def new_proposal(
    timestep: int,
    id: int,
    proposer: str,
    scenario: Scenario,
    proposal_type: ProposalType = None,
    sub_type: ProposalSubType = None,
    attack_targets: set = {},
    cancelable: bool = True,
) -> Proposal:
    proposal = Proposal(id=id, timestep=timestep, proposal_type=proposal_type, sub_type=sub_type, cancelable=cancelable)
    proposal.proposer = proposer

    if proposal_type is None:
        proposal.proposal_type = determine_proposal_type(scenario)

    if sub_type is None:
        proposal.sub_type = determine_proposal_subtype(scenario)

    proposal.damage = determine_proposal_damage(proposal.proposal_type)
    proposal.attack_targets = attack_targets

    return proposal


def get_proposal_by_id(proposals: List[Proposal], id: int) -> Proposal:
    for proposal in proposals:
        if proposal.id == id:
            return proposal

    return None
