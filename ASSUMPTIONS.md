\usepackage{amsmath}

# Model Assumptions

This document outlines the key assumptions made during the development of the Lido Dual Governance model. These assumptions are crucial for understanding the model's behavior, limitations, and potential areas for future refinement.

## Actors Distributions

The main actors in the system are based on stETH/wstETH token holders on the Ethereum chain. The on-chain data used for defining actors includes, but is not limited to:

- Token holder wallet address
- Balance of stETH tokens
- Balance of wstETH tokens
- Token holder label (such as protocol name, token holder classification)
- Address type (EOA, Smart Contract, CEX, and Custody holdings)
- Protocol type (for Smart Contracts)

Using an initial set of data from on-chain sources, the model uses over 1200 wallet addresses, representing over 80% of the total token supply of stETH in the market. The remaining 20% is left out of scope as it is distributed across over 400,000 wallets, which affects overall model performance.

## Model Actor's Classification

Each actor inside the model is assigned different variables that affect their behavior in the model:

- **Actor's Health (value between 0 to 100):** Represents the overall health or stability of the actor.
- **Actor Behavior Type:** Defines the actor's role in the system, such as honest behavior, single/coordinated attackers, and defenders.
- **Reaction Type:** Determines how quickly the actor reacts to changing environments, categorized as Quick, Normal, or Slow reactions.

# Statistical Distributions

The Lido Dual Governance model relies on statistical distributions to generate a unique environment on each simulation run (with different `seed` values).

## Actor's Health Distribution

The model uses a normal distribution of health among all wallets presented from the on-chain data (over 1200 wallets).

- **Mean Health:** 50 HP units
- **Standard Deviation:** 20 HP units

According to this normal distribution, health is distributed as follows:

- Actors with HP between 25 and 75 units account for **78.87%** of all actors (~951-952 wallets).
- Actors with less than 25 HP account for **10.56%** of all actors (~127-128 wallets).
- Actors with over 90 HP account for **2.28%** of all actors (~27-28 wallets).

// TODO: add health distribution picture here

### Determining Actor Health

The `determine_actor_health` function uses a normal distribution to assign health values to actors. The health value is constrained between 1 and 100.

```python
def determine_actor_health(scenario: Scenario, mean_health=50, std_dev_health=20):
    rng = get_rng()

    health_value = int(rng.normal(mean_health, std_dev_health))
    health = max(1, min(100, health_value))

    return health
```

## Distribution of Actor's Behavior

Simulation input parameters affect the distribution of actors' behaviors in the model. These behaviors can be decided in advance and provided as a set of addresses representing attackers and defenders in the system. Alternatively, they can be decided based on the simulated scenario:

In `Happy Path` Scenario: All actors in the system behave honestly, without anyone trying to disrupt normal operations of the Dual Governance system.

For Attack Scenarios (`Single Attack` and `Coordinated Attack`) Actor's behavior is distributed using a normal distribution:

- **Mean Value:** 0
- **Standard Deviation:** 1

For values higher or equal to 3σ, the actor's behavior is assigned as an attacker. This means that on average, there is a **0.013%** probability of an actor being an attacker. With the existing number of actors modeled, the number of attackers could be between ~1-6 actors in a simulation run.

## Actor's Reaction Time

The reaction time of actors in the model is a crucial factor that influences how quickly actors respond to changes in the environment. The reaction time is categorized into three types: Quick, Normal, and Slow. The `determine_reaction_time` function uses a normal distribution to assign reaction times based on the specified reaction model.

### Reaction Time Categories

- **Quick Reaction:** Actors respond very quickly to changes in the environment.
- **Normal Reaction:** Actors respond at a typical or average speed.
- **Slow Reaction:** Actors respond slowly to changes in the environment.

### Determining Reaction Time

The `determine_reaction_time` function uses a normal distribution with a mean of 0 and a standard deviation of 1 to generate a reaction time value. This value is then used to categorize the reaction time based on the specified reaction model.

- **Quick Reaction** (Reaction time ≥ 2σ):

  - **Percentage**: Approximately 2.28% of all actors.
  - **Number of Actors**: ~27-28 actors (assuming 1200 actors).

- **Normal Reaction** (1σ ≤ Reaction time < 2σ):

  - **Percentage**: Approximately 13.59% of all actors.
  - **Number of Actors**: ~163-164 actors (assuming 1200 actors).

- **Slow Reaction** (Reaction time < 1σ):
  - **Percentage**: Approximately 84.13% of all actors.
  - **Number of Actors**: ~1009-1010 actors (assuming 1200 actors).

### Code Implementation

The `determine_reaction_time` function is implemented as follows:

```python
def determine_reaction_time() -> ReactionTime:
    rng = get_rng()
    reaction_time_value = rng.normal(0, 1)

    if reaction_time_value >= 2:
        return ReactionTime.Quick
    elif reaction_time_value >= 1:
        return ReactionTime.Normal
    else:
        return ReactionTime.Slow
```

## Actor's Reaction Delay

Actor's reaction delay is registered on each update of actor's health. For example if actor received damage from the proposal in Dual Governance system, his reaction is updated. This reaction delay affects the time in which this actor activates its behavior according to external factors in the model. Such actions include: Lock/Unlock stETH/wstETH tokens into Signalling Escrow based on Actor's HP units.

### Model Parameters for Reaction Delay

The reaction delay parameters are defined in seconds and represent the maximum delay times for different reaction types. These parameters are used in the `calculate_reaction_delay` function to determine the reaction delay based on the **Actor's Reaction Type**.

### Reaction Delay Model Parameters

- **`slow_actor_max_delay`**: Maximum delay time for Slow Reaction.

  - **Description**: This represents a maximum delay of 15 days for actors with a Slow Reaction.

- **`normal_actor_max_delay`**: Maximum delay time for Normal Reaction.

  - **Description**: This represents a maximum delay of 5 days for actors with a Normal Reaction.

- **`quick_actor_max_delay`**: Maximum delay time for Quick Reaction.
  - **Description**: This represents a maximum delay of 1 day for actors with a Quick Reaction.

### Reaction Delay Breakdown

- **Quick Reaction** Reaction delay is generated between 0 and quick_actor_max_delay (1 day).
- **Normal Reaction** Reaction delay is generated between quick_actor_max_delay (1 day) and normal_actor_max_delay (5 days).
- **Slow Reaction** Reaction delay is generated between normal_actor_max_delay (5 days) and slow_actor_max_delay (15 days).
- **No Reaction** Reaction delay is set to `Timestamp.MAX_VALUE`, indicating no response.

### Code Implementation

#### `calculate_reaction_delay` Function

The `calculate_reaction_delay` function determines the reaction delay based on the actor's reaction type. It uses the `generate_reaction_delay` function to generate a random reaction delay within a specified range for Quick, Normal, and Slow reactions. For No Reaction, it returns a maximum delay value.

```python
def calculate_reaction_delay(samples, reaction: ReactionTime) -> int:
    match reaction:
        case ReactionTime.Slow:
            return generate_reaction_delay(normal_actor_max_delay, slow_actor_max_delay)
        case ReactionTime.Normal:
            return generate_reaction_delay(quick_actor_max_delay, normal_actor_max_delay)
        case ReactionTime.Quick:
            return generate_reaction_delay(0, quick_actor_max_delay)
        case ReactionTime.NoReaction:
            return Timestamp.MAX_VALUE

```

#### `generate_reaction_delay` Function

The `generate_reaction_delay` function generates a random reaction delay within a specified range using a log-normal distribution. It scales the generated reaction times to fit within the specified minimum and maximum delay times.

```python
def generate_reaction_delay(min_time, max_time):
    rng = get_rng()
    
    samples = rng.lognormal(mean=1, sigma=0.5, size=1000)
    scaled_reaction_times = (samples - np.min(samples)) / (np.max(samples) - np.min(samples)) * (
        max_time - min_time
    ) + min_time

    reaction_delay = rng.choice(scaled_reaction_times, p=None)

    return int(reaction_delay)
```

## Actor's Reaction Delay (proposition)
Actor's reaction delay is generated **every time actor's health gets updated**. Actor's heath is updated when proposals are submitted or cancelled. Depending on the circumstances actors can try to either **lock** their tokens in escrow or **unlock** them. Actor will try to lock the tokens if her **health becomes less or equal to zero**. Actor will try to unlock the locked tokens if her **health goes above zero**. Every timestep the conditions above are checked and locking\unlocking occurs if the reaction delay is smaller than the time elapsed since the earliest proposal submission that was not cancelled.

### Model Parameters for Reaction Delay
The reaction delay is sampled from the log-normal distribution with parameters $\mu$ and $\sigma$. For each Reaction Time there is a specific log-normal distribution, that is determined by two parameters: median delay and 99 percentile delay. These two parameters uniquely identify $\mu$ and $\sigma$.

- **`slow_actor_median_delay`**: Time in seconds, representing 10 days. The probability that a Slow Actor reacts before this time is $0.5$. 
- **`slow_actor_99_delay`**: Time in seconds, representing 15 days. The probability that a Slow Actor reacts before this time is $0.99$.
- **`normal_actor_median_delay`**: Time in seconds, representing 3 days. The probability that a Normal Actor reacts before this time is $0.5$.
- **`normal_actor_99_delay`**: Time in seconds, representing 10 days. The probability that a Normal Actor reacts before this time is $0.99$.
- **`quick_actor_median_delay`**: Time in seconds, representing 12 hours. The probability that a Quick Actor reacts before this time is $0.5$.
- **`quick_actor_99_delay`**: Time in seconds, representing 1 day. The probability that a Quick Actor reacts before this time is $0.99$.


#### `generate_reaction_delay` Function

The `generate_reaction_delay` function generates a random reaction delay within a specified range using a log-normal distribution. In the function log-normal distribution parameters $\mu, \sigma$ are determined based on desired median and p% percentile.

```python
def generate_reaction_delay(median_delay, p_percentile_delay, p=.99):
    mu = np.log(median_delay)
    standard_normal_p_percentile = scipy.stats.norm.isf(1 - p)
    sigma = (np.log(p_percentile_delay) - mu) / standard_normal_p_percentile

    rng = get_rng()
    reaction_delay = rng.lognormal(mean=mu, sigma=sigma)
    reaction_delay = int(np.round(reaction_delay))

    return reaction_delay
```
![Resulting reaction delay distributions](/images/ReactionDelayDistributions.png "ReactionDelayDistributions")
# Proposal Generation

The proposal generation in the model is determined by several functions that define the type, subtype, and damage of proposals based on the scenario and a normal distribution. These functions help simulate different types of proposals that can impact the governance system.

### Proposal Types and Subtypes

- **ProposalType.Random**: A proposal with random impact.
- **ProposalType.NoImpact**: A proposal with no significant impact.
- **ProposalType.Negative**: A proposal with negative impact.
- **ProposalType.Danger**: A proposal with high risk and potential for significant damage.
- **ProposalType.Hack**: A proposal representing a smart contract hack.

### Proposal Subtypes

- **ProposalSubType.Bribing**: A subtype of proposal involving bribery.
- **ProposalSubType.FundsStealing**: A subtype of proposal involving funds stealing.

### Proposal Damage Values

- **ProposalType.Positive**: Damage ranges from -5 to -25.
- **ProposalType.Negative**: Damage ranges from 5 to 25.
- **ProposalType.Random**: Damage ranges from -25 to 25.
- **ProposalType.NoImpact**: Damage ranges from -2 to 2.
- **ProposalType.Danger**: Damage is fixed at 100.
- **ProposalType.Hack**: Damage is fixed at 200.

## Proposal Type Breakdown Based on Normal Distribution

The proposal type is determined using a normal distribution with a mean of 0 and a standard deviation of 1. The distribution value is used to categorize the proposal type based on the scenario.

### Happy Path Scenario

- **ProposalType.Random**: Distribution value ≥ 1 or ≤ -1 (approximately 31.73% of proposals).
- **ProposalType.NoImpact**: Distribution value between -1 and 1 (approximately 68.27% of proposals).

### Single Attack and Coordinated Attack Scenarios

- **ProposalType.Negative**: Distribution value ≥ 2 or ≤ -2 (approximately 4.56% of proposals).
- **ProposalType.Danger**: Distribution value between -2 and 2 (approximately 95.44% of proposals).

### Smart Contract Hack Scenario

- **ProposalType.Danger**: Distribution value ≥ 2 or ≤ -2 (approximately 4.56% of proposals).
- **ProposalType.Hack**: Distribution value between -2 and 2 (approximately 95.44% of proposals).

## Proposal Subtype Breakdown Based on Normal Distribution

The proposal subtype is determined using a normal distribution with a mean of 0 and a standard deviation of 1. The distribution value is used to categorize the proposal subtype based on the scenario.

### Single Attack and Coordinated Attack Scenarios

- **ProposalSubType.Bribing**: Distribution value ≥ 2 or ≤ -2 (approximately 4.56% of proposals).
- **ProposalSubType.FundsStealing**: Distribution value between -2 and 2 (approximately 95.44% of proposals).

## Code implementation

#### `determine_proposal_type` Function

The `determine_proposal_type` function determines the type of proposal based on the scenario and a normal distribution. The proposal type can be one of several categories, each representing a different impact on the system.

```python
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
```

#### `determine_proposal_subtype` Function

The `determine_proposal_subtype` function determines the subtype of the proposal based on the scenario and a normal distribution. The proposal subtype provides additional detail about the nature of the proposal.

```python
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
```

#### `determine_proposal_damage` Function

The `determine_proposal_damage` function determines the damage caused by the proposal based on its type. The damage is a numerical value that represents the impact of the proposal on the system.

```python
def determine_proposal_damage(proposal_type: ProposalType) -> int:
    rng = get_rng()
    damage: int = 0

    match proposal_type:
        case ProposalType.Positive:
            damage = rng.uniform(-5, -25)
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

    return damage
```

# Future Considerations

- **Inclusion of Smaller Holders:** Consider ways to include the remaining 20% of stETH holders in future iterations of the model.
- **Behavioral Variability:** Explore more complex behavioral models to capture a wider range of actor behaviors.
- **Health Distribution:** Investigate the impact of different health distribution models on simulation outcomes.
- **Dynamic Reaction Models**: Explore the possibility of dynamically adjusting reaction models based on real-time data or specific scenarios.
- **Reaction Time Variability**: Investigate the impact of varying reaction time distributions on simulation outcomes.
