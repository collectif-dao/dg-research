import numpy as np

from model.sys_params import normal_actor_max_delay, quick_actor_max_delay, slow_actor_max_delay
from model.types.governance_participation import GovernanceParticipation
from model.types.reaction_time import ModeledReactions, ReactionTime
from specs.types.timestamp import Timestamp


def calculate_reaction_delay(samples, reaction: ReactionTime) -> int:
    match reaction:
        case ReactionTime.Slow:
            return generate_reaction_delay(samples, normal_actor_max_delay, slow_actor_max_delay)
        case ReactionTime.Normal:
            return generate_reaction_delay(samples, quick_actor_max_delay, normal_actor_max_delay)
        case ReactionTime.Quick:
            return generate_reaction_delay(samples, 0, quick_actor_max_delay)
        case ReactionTime.NoReaction:
            return Timestamp.MAX_VALUE


def generate_reaction_delay(samples, min_time, max_time):
    scaled_reaction_times = (samples - np.min(samples)) / (np.max(samples) - np.min(samples)) * (
        max_time - min_time
    ) + min_time

    reaction_delay = np.random.choice(scaled_reaction_times, p=None)

    return int(reaction_delay)


def determine_reaction_time(reactions: ModeledReactions) -> ReactionTime:
    reaction_time_value = np.random.normal(0, 1)

    match reactions:
        case ModeledReactions.Normal:
            if reaction_time_value >= 2:
                return ReactionTime.Quick
            elif reaction_time_value >= 1:
                return ReactionTime.Normal
            else:
                return ReactionTime.Slow

        case ModeledReactions.Accelerated:
            if reaction_time_value >= 1.6:
                return ReactionTime.Quick
            elif reaction_time_value >= 0.8:
                return ReactionTime.Normal
            else:
                return ReactionTime.Slow

        case ModeledReactions.Slowed:
            if reaction_time_value >= 2.2:
                return ReactionTime.Quick
            elif reaction_time_value >= 1.25:
                return ReactionTime.Normal
            else:
                return ReactionTime.Slow


def determine_governance_participation(reactions: ModeledReactions) -> GovernanceParticipation:
    participation_value = np.random.normal(0, 1)

    if participation_value >= 2:
        return GovernanceParticipation.Full
    elif participation_value >= 1:
        return GovernanceParticipation.Normal
    else:
        return GovernanceParticipation.Abstaining
