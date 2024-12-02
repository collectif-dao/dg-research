import numpy as np
import scipy.stats

from model.sys_params import normal_actor_max_delay, quick_actor_max_delay, slow_actor_max_delay
from model.types.governance_participation import GovernanceParticipation
from model.types.reaction_time import ModeledReactions, ReactionTime
from model.utils.seed import get_rng

### TODO: 1. refactor random variables into the separate module. They have to be defined and calculated only at startup.
### TODO: 2. Reaction delay needs to be dependent on params on specs/parameters.py. But the relationship is yet to be defined.


def determine_shift_mu_sigma(left_bound, right_bound, p=0.99, median_parameter=0.5):
    """
    Calculates parameters (shift, mu, sigma) for shifted log-normal distribution.
    The probability that a rv from the distribution lies between left_bound and right_bound is set by p.
    The median of the distribution is set equal to left_bound + (right_bound - left_bound) * median_parameter.

    Parameters
    ----------
    left_bound : float
        The left border of the distribution, P(x < left_bound) = 0
    right_bound : float
        The right border of the distribution, P(x < right_bound) = p
    p : float, optional
        The number between 0 and 1 used to calculate sigma. See right_bound parameter for details. Default is .99.
    median_parameter : float
        The number between 0 and 1 used to determine the median position between left_bound and right_bound. Default is .5.

    Returns
    -------
        shift : float
            The value to add to the log-normal random variable. P(x < shift) = 0.
        median : float
            The np.log(median) is the parameter mu of the underlying normal distribution.
        sigma : float
            The parameter sigma of the underlying normal distribution.

        To sample a random variable from the distribution one can use
            shift + np.random.lognormal(mean=np.log(median), sigma=sigma)
        or
            scipy.stats.lognorm.rvs(s=sigma, loc=shift, scale=median).
    """
    p_window_width = right_bound - left_bound
    median = p_window_width * median_parameter
    standard_normal_p_percentile = scipy.stats.norm.isf(1 - p)
    sigma = -np.log(median_parameter) / standard_normal_p_percentile
    return left_bound, median, sigma


def get_reaction_delay_random_variable(min_time, max_time, p=0.99, median_parameter=0.5, shifted=False):
    """
    Calculates parameters for reaction delay distribution which is assumed to be (shifted) log-normal and returns the frozen scipy.stats.lognorm object with set parameters.
    The min_time and max_time parameters control the location of the distribution. P(x < max_time) = p.
    The median of the distribution is located between min_time and max_time, the exact location is controlled by the median_parameter.
    E.g. if median_parameter=.5, the median is halfway between min_time and max_time.
    If shifted == True, then the reaction delay lies in the open interval (min_time, inf).
    Else the reaction delay lies in the open interval (0, inf), but the p-th percentile and the median stay the same.

    Parameters
    ----------
    min_time : float
    max_time : float
    p : float
    median_parameter : float
    shifted : bool, optional
        Default is False.

    Returns
    -------
    scipy.stats.lognorm object
    """
    if shifted:
        shift, median, sigma = determine_shift_mu_sigma(
            left_bound=min_time, right_bound=max_time, p=p, median_parameter=median_parameter
        )
    else:
        median_parameter_adjusted = median_parameter + (1 - median_parameter) * min_time / max_time
        shift, median, sigma = determine_shift_mu_sigma(
            left_bound=0, right_bound=max_time, p=p, median_parameter=median_parameter_adjusted
        )
    rv = scipy.stats.lognorm(s=sigma, loc=shift, scale=median)
    return rv


def generate_reaction_delay(reaction_time: int) -> int:
    rng = get_rng()
    # match reaction:
    #     case 2:
    #         left_bound, right_bound = 0, quick_actor_max_delay
    #     case 1:
    #         left_bound, right_bound = quick_actor_max_delay, normal_actor_max_delay
    #     case 3:
    #         left_bound, right_bound = normal_actor_max_delay, slow_actor_max_delay
    #     case 4:
    #         return Timestamp.MAX_VALUE
    # reaction_delay_random_variable = get_reaction_delay_random_variable(left_bound, right_bound)
    reaction_delay_random_variable = reaction_delay_random_variables[reaction_time]
    reaction_delay = reaction_delay_random_variable.rvs(random_state=rng)
    return reaction_delay


def generate_reaction_delay_vector(reaction_time: np.ndarray):
    rng = get_rng()
    reaction_delay = np.zeros(len(reaction_time), dtype="int64")

    for reaction_time_key, random_variable in reaction_delay_random_variables.items():
        mask = reaction_time == reaction_time_key
        size = np.sum(mask)
        reaction_delay[mask] = np.ceil(random_variable.rvs(random_state=rng, size=size)).astype("int64")

    return reaction_delay


def determine_reaction_time(reactions: ModeledReactions) -> ReactionTime:
    rng = get_rng()
    reaction_time_value = rng.normal(0, 1)

    match reactions:
        case ModeledReactions.Normal:
            if reaction_time_value >= 2:
                return 2
            elif reaction_time_value >= 1:
                return 1
            else:
                return 3

        case ModeledReactions.Accelerated:
            if reaction_time_value >= 1.6:
                return 2
            elif reaction_time_value >= 0.8:
                return 1
            else:
                return 3

        case ModeledReactions.Slowed:
            if reaction_time_value >= 2.2:
                return 2
            elif reaction_time_value >= 1.25:
                return 1
            else:
                return 3


def determine_reaction_time_vector(size, reactions: ModeledReactions):
    rng = get_rng()
    reaction_time_values = np.array(rng.normal(0, 1, size=size))

    reaction_times = np.zeros(size, dtype="int8") + ReactionTime.Slow.value

    match reactions:
        case ModeledReactions.Normal:
            normal_cutoff = 1
            quick_cutoff = 2
        case ModeledReactions.Slowed:
            normal_cutoff = 1.25
            quick_cutoff = 2.2
        case ModeledReactions.Accelerated:
            normal_cutoff = 0.8
            quick_cutoff = 1.6

    normal_mask = np.all(
        (
            reaction_time_values >= normal_cutoff,
            reaction_time_values < quick_cutoff,
        ),
        axis=0,
    )

    reaction_times[normal_mask] = ReactionTime.Normal.value
    reaction_times[reaction_time_values >= quick_cutoff] = ReactionTime.Quick.value
    return reaction_times


def determine_governance_participation(reactions: ModeledReactions) -> GovernanceParticipation:
    rng = get_rng()
    participation_value = rng.normal(0, 1)

    if participation_value >= 2:
        return 2
    elif participation_value >= 1:
        return 1
    else:
        return 3


def determine_governance_participation_vector(size, reactions):
    rng = get_rng()
    participation_values = np.array(rng.normal(0, 1))
    participation = np.zeros(size, dtype="uint8") + GovernanceParticipation.Abstaining.value
    participation[participation_values >= 2] = GovernanceParticipation.Full.value
    participation[participation_values >= 1] = GovernanceParticipation.Normal.value
    return participation


class ConstantRandomVariable:
    def __init__(self, value):
        self.value = value

    def rvs(self, size=None, random_state=None):
        if size is None:
            return self.value
        return np.repeat(self.value, size)


reaction_delay_random_variables = {
    ReactionTime.NoReaction.value: ConstantRandomVariable(2**32 - 1),  # 4
    ReactionTime.Slow.value: get_reaction_delay_random_variable(normal_actor_max_delay, slow_actor_max_delay),  # 3
    ReactionTime.Normal.value: get_reaction_delay_random_variable(quick_actor_max_delay, normal_actor_max_delay),  # 1
    ReactionTime.Quick.value: get_reaction_delay_random_variable(0, quick_actor_max_delay),  # 2
}


def generate_initial_reaction_time_vector(reaction_time: np.ndarray):
    rng = get_rng()
    reaction_time_vector = np.zeros(len(reaction_time), dtype=np.int64)
    reaction_time_vector[reaction_time == ReactionTime.NoReaction.value] = 2**32 - 1
    mask_slow = reaction_time == ReactionTime.Slow.value
    reaction_time_vector[mask_slow] = scipy.stats.uniform.rvs(
        0, slow_actor_max_delay, size=sum(mask_slow), random_state=rng
    )
    mask_normal = reaction_time == ReactionTime.Normal.value
    reaction_time_vector[mask_normal] = scipy.stats.uniform.rvs(
        0, normal_actor_max_delay, size=sum(mask_normal), random_state=rng
    )
    mask_quick = reaction_time == ReactionTime.Quick.value
    reaction_time_vector[mask_quick] = scipy.stats.uniform.rvs(
        0, quick_actor_max_delay, size=sum(mask_quick), random_state=rng
    )

    return reaction_time_vector
