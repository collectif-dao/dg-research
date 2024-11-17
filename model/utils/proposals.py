from model.types.proposals import ProposalSubType, ProposalType
from model.types.scenario import Scenario
from model.utils.seed import get_rng
from specs.dual_governance.proposals import Proposals, ProposalStatus


def determine_proposal_type(scenario: Scenario) -> ProposalType:
    rng = get_rng()

    distribution = rng.normal(0, 1)

    match scenario:
        case Scenario.HappyPath:
            if distribution >= 1 or distribution <= -1:
                return ProposalType.Random
            else:
                return ProposalType.NoImpact

        case Scenario.SingleAttack:
            if distribution >= 2 or distribution <= -2:
                return ProposalType.Negative
            else:
                return ProposalType.Danger

        case Scenario.CoordinatedAttack:
            if distribution >= 2 or distribution <= -2:
                return ProposalType.Negative
            else:
                return ProposalType.Danger

        case Scenario.SmartContractHack:
            if distribution >= 2 or distribution <= -2:
                return ProposalType.Danger
            else:
                return ProposalType.Hack

        case Scenario.VetoSignallingLoop:
            if distribution >= 2 or distribution <= -2:
                return ProposalType.Random
            else:
                return ProposalType.Positive


def determine_proposal_subtype(scenario: Scenario) -> ProposalSubType:
    rng = get_rng()
    distribution = rng.normal(0, 1)

    match scenario:
        case Scenario.HappyPath:
            return ProposalType.NoImpact

        case Scenario.SingleAttack:
            if distribution >= 2 or distribution <= -2:
                return ProposalSubType.Bribing
            else:
                return ProposalSubType.FundsStealing

        case Scenario.CoordinatedAttack:
            if distribution >= 2 or distribution <= -2:
                return ProposalSubType.Bribing
            else:
                return ProposalSubType.FundsStealing

        case Scenario.VetoSignallingLoop:
            return ProposalType.NoImpact


def determine_proposal_damage(proposal_type: ProposalType) -> int:
    rng = get_rng()
    damage: int = 0

    match proposal_type:
        case ProposalType.Positive:
            damage = rng.uniform(-25, -5)
        case ProposalType.Negative:
            damage = rng.uniform(5, 25)
        case ProposalType.Random:
            damage = rng.uniform(-25, 25)
        case ProposalType.NoImpact:
            damage = rng.uniform(-2, 2)
        case ProposalType.Danger:
            damage = 100
        case ProposalType.Hack:
            damage = 200

    return int(damage)


def get_first_proposal_timestamp(proposals: Proposals):
    proposal_list = proposals.state.proposals

    submitted_timestamps = [
        proposal.submittedAt.value
        for proposal in proposal_list
        if (proposal.status == ProposalStatus.Submitted or proposal.status == ProposalStatus.Scheduled)
        and not proposals.is_proposal_marked_cancelled(proposal.id)
    ]
    scheduled_timestamps = [
        proposal.scheduledAt.value
        for proposal in proposal_list
        if (proposal.status == ProposalStatus.Scheduled or proposal.status == ProposalStatus.Executed)
        and not proposals.is_proposal_marked_cancelled(proposal.id)
    ]

    all_timestamps = submitted_timestamps + scheduled_timestamps

    return min(all_timestamps, default=0)


def iterable_proposals(proposals, last_cancelled_proposal_id, total_count):
    start_index = next(
        (index for index, proposal in enumerate(proposals) if proposal.id == last_cancelled_proposal_id), None
    )

    if start_index is None:
        return None

    # start_index += 1
    end_index = start_index + total_count
    end_index = min(end_index, len(proposals))

    iterated_proposals = proposals[start_index:end_index]

    return iterated_proposals
