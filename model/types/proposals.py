from dataclasses import dataclass, field
from typing import List, Set

from model.types.proposal_type import ProposalSubType, ProposalType
from model.types.scenario import Scenario
from model.utils.proposals import determine_proposal_damage, determine_proposal_subtype, determine_proposal_type


@dataclass
class Proposal:
    proposal_type: ProposalType = field(default_factory=lambda: ProposalType.NoImpact)
    proposer: str = field(default_factory=lambda: "")
    id: int = 0
    damage: int = 0
    timestep: int = 0
    sub_type: ProposalSubType = field(default_factory=lambda: ProposalSubType.NoEffect)
    attack_targets: Set[str] = field(default_factory=lambda: set())


def new_proposal(
    timestep: int,
    id: int,
    proposer: str,
    scenario: Scenario,
    proposal_type: ProposalType = ProposalType.NoImpact,
    subtype: ProposalSubType = ProposalSubType.NoEffect,
) -> Proposal:
    proposal = Proposal(id=id, timestep=timestep, proposal_type=proposal_type, sub_type=subtype)
    proposal.proposer = proposer

    if proposal_type == ProposalType.NoImpact:
        proposal.proposal_type = determine_proposal_type(scenario)

    if subtype == ProposalSubType.NoEffect:
        proposal.sub_type = determine_proposal_subtype(scenario)

    proposal.damage = determine_proposal_damage(proposal.proposal_type)

    return proposal


def get_proposal_by_id(proposals: List[Proposal], id: int) -> Proposal:
    for proposal in proposals:
        if proposal.id == id:
            return proposal

    return None
