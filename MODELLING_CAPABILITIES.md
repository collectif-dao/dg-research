# Model Capabilities

This document outlines the key simulation capabilities of the model developed for Lido Dual Governance. These capabilities allow to understand, which elements of DG are now parametrized for simulations, what type of questions the model can take, and which answers it can provide.

## Main simulation pathways 

The model provides a framework to create simulation scenarios to validate DG under different conditions. In general, there are two major scenario groups:
- Regular system behavior - DG life without major proposals or attacks
- Irregular system behavior - specific cases like attacks, DG bottlenecks, significant market fluctuations, external hacks, etc.

## Current model state

At the moment, the model is capable of simulating the following groups of scenarios:
- Normal Dual Governance operations (multiple months of DG life with random proposal generated for DG)
- Attacks on the entire protocol (predefined attacking proposal on the Lido Protocol, e.g. withdrawals queue target wallet replacement)
- Attacks on specific elements of protocol (predefined attacking proposal or sequence of proposals, e.g. "permanent" Veto Signaling lock)
- Testing specific parameters of DG (number of Monte-Carlo simulations to test different values of isolated DG parameters)

## Parametrized elements of DG 

To further understand model capabilities, the list of main variable parameters for scenario definition is provided below.
- Actor parameters
  - Wallet information (token balances)
  - Wallet type (CEX, Private, Smart Contract, ...)
  - Reaction time (% of slow, normal, fast and non-voting actors)
  - HP of actors (parametrized independent escrow lock decision for each actor)
  - Wallet labels (changes proposal HP effects on actor)
- DG parameters
  - Governance % thresholds (Signaling, Ragequit, ...)
  - Governance time parameters (Time to proposal approval, Signaling duration, Timelock, Cooldown, ...)
- Proposal parameters
  - Defined attackers/beneficiaries
  - Defined protectors of protocol
  - Cancellation point (After signaling, no cancellation, ...)
  - Attack vector (Value capture, DG lock, ...)
  - Scenario duration (Number of timesteps)
 
# Scenario analytics

For each scenario, a Jupiter Notebook is created and the following analytics could be provided for each scenario:
- General scenario analytics
<img src="https://github.com/user-attachments/assets/d42f0010-5549-4f0a-9be1-c4382bbedb60" width="400"/>

- Actor distribution analytics
<img src="https://github.com/user-attachments/assets/e07ebd34-58f4-4144-8392-a3a95c9d37aa" width="600"/>

- Actor reaction time analytics
<img src="https://github.com/user-attachments/assets/0373353d-338d-46cb-9871-a32e9a0bc33e" width="600"/>

- Wallet type analytics
<img src="https://github.com/user-attachments/assets/b1a08714-13be-49a4-ac6c-b192243831ef" width="600"/>

- Threshold to active user ratio
<img src="https://github.com/user-attachments/assets/91111b7c-358b-49c1-b73f-0bbb53aa6494" width="400"/>

- Groups combination to Signaling threshold
<img src="https://github.com/user-attachments/assets/318d5f4a-f6d9-4637-895d-2a7946693177" width="600"/>

- Time before Veto Signaling over multiple runs
<img src="https://github.com/user-attachments/assets/c82b9d36-dd3a-4643-bd70-d20f643ecf6f" width="400"/>

- Comparison locked amount at each timestep over multiple runs with different thresholds
<img src="https://github.com/user-attachments/assets/732a7d41-c35c-4f0e-8c85-2636a3804d3b" width="800"/>

- Distributions of voting with confidence intervals over multiple runs
<img src="https://github.com/user-attachments/assets/4614b8db-5ae7-4fa5-9988-73a226003211" width="800"/>

## Tested scenario templates

List of currently completed test scenarios with key test points:

Global System tests
- X runs of Normal Dual Governance operations for 3 months [[Example Notebook](experiments/notebooks/01_model_validation.ipynb)]
  - Tests that all parts of the code are working correctly together
  - Tests HP model in general case
  - Check whether DG simulation works well without external pressure
  - Test whether all components of DG proposals, voting, etc. work correctly
- Fund stealing attack on the entire protocol [[Example Notebook](experiments/notebooks/02_withdrawal_queue_attack.ipynb)]
  - Tests inputs of simple attack scenarios on the system
  - Tests agents' behavior under attack
  - Tests HP model in an attack scenario
  - Test of DG state change (Signaling, Ragequit, Cooldown, ...)
 
DG parameter-specific tests
- Simulation of scenarios with different user reaction times assignment [[Example Notebook](experiments/notebooks/04_withdrawal_queue_attack_institutional.ipynb)]
  - Testing actor reaction time assumptions
  - Testing scenarios with different distributions of slow, normal and fast users
  - Parametrizing token ownership per group and testing their ability to react to proposals in time
- Simulation of various veto signaling and ragequit threshold parameters [[Example Notebook 1](experiments/notebooks/05_singalling_threshold_sweeps_under_proposal_with_attack.ipynb)] [[Example Notebook 2](experiments/notebooks/06_ragequit_threshold_sweep.ipynb)] 
  - Time to signaling
  - Time to ragequit
  - Is there enough active actors to react in time
- Veto Signaling loop attack [[Example Notebook](experiments/notebooks/06_veto_signalling_loop.ipynb)] 
  - Number of coordinated users needed to keep this system loop
  - Change of DG states in case of continuous loop
  - Loop duration potential
- Group label reaction time decrease [[Example Notebook](experiments/notebooks/04_withdrawal_queue_attack_institutional.ipynb)] 
  - What % of slow actors break the system from reacting in time on problem proposals
  - What % of active wallets+funds is needed to keep the system safe from attacks

Instructions on how to run simulations locally are available [here](README.md)

## Possible questions to be answered

Here are some examples of questions that the model can currently answer:
- Do all parts of DG work properly?
- Can signaling be randomly activated in regular DG flow? (threshold too low?)
- What could be different actor reaction time distribution assumptions and what could they affect?
- Will DG reach thresholds in set timelines given specific actor reaction distribution?
- What could be the maximal thresholds for Veto Signalling given specific actor reaction distribution?
- What is the cost requirement for specific attacks (e.g. loop)?
- How many actors are needed to coordinate (stETh wallet distribution)?
- Which wallets can be in 1,2,3 coordination per threshold?

Plus, any specific questions to test numeric model parameters could be asked or specific attack scenarios could be simulated.

## Scenarios in the research pipeline (on 2024.09.30)

Actor Labels:
- Provide a variety of labels in the model to define proposal impacts per label group
- How general system health will be affected if the majority of proposals are biased toward specific groups of actors in the system and harm others

DAO and stETH misalignment:
- Cost of misaligned decision (e.g. DAO decision goes against community → cost of decision)

Restaking protocol captures Lido:
- Restaking contract gets upgraded and now is an active member of a Dual Governance system. How will it affect the system?
- Restaking contract vetoes upgrade of protocol fee (e.g. from 10% to 12%)
- Restaking contract trying to push an upgrade of the protocol fee (e.g. from 10% to 5%)

Bribing:
- Single attacker trying to push Withdrawal Queue contract upgrade with bribes of 50% of users by stealing funds from another 50% of users (using Lido internal capital)
- Cluster of coordinated attackers push proposal to replace the Withdrawal Queue and uses external capital to bribe users (bribing with active rebalancing)

Smart contract hacks:
- Hack of a smart contract with substantial funds. Attacker uses stETH/wstETH funds to capture dual governance effectively having a veto loop in overall Lido DAO.
- Smart contract hack where attacker wants to withdraw funds via the withdrawal queue, simulate such attack from the Lido side to minimize the effect of attack

General:
- Coordinated group has enough funds to veto good proposals and postpone their execution
- Bribe of Tiebreaker Committee members from a cluster of coordinated attackers trying to push a proposal favoring their goals (not necessarily an attack on the Lido DAO)
- Rage Quit scenario with standard Withdrawal Queue operations 
- Rage Quit scenario with Node Operators declining exits and not fulfilling requests for withdrawals from the stake
- System deal lock in which Tiebreaker Committee is activated and resolves an issue
- Normal Dual Governance operations
- Apply slow reaction as the majority of stETH/wstETH funds are in the hands of Institutional actors
- Long-term lock of Dual Governance system by a cluster of coordinated attackers having over 20% of total supply, which targets Rage Quit state for Dual Governance

