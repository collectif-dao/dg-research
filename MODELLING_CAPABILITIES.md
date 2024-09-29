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

To further understand model capabilities, the list of variable parameters for scenarios definition is provided below.
- Actor parameters
  - Wallet information (token balances)
  - Wallet type (CEX, Private, Smart Contract, ...)
  - Reaction time (% of slow, normal, fast and non-voting actors)
  - HP of actors (parametrized independent escrow lock decision for each actor)
  - (TBD) Wallet label (changes proposal HP effects on actor)
- DG parameters
  - Governance % thresholds (Signaling, Ragequit, ...)
  - Governance time parameters (Time to proposal approval, Signaling duration, Timelock, Cooldown, ...)
- Proposal parameters
  - Defined attackers/beneficiaries
  - Defined protectors of protocol
  - Cancelation point (After signaling, no cancelation, ...)
  - Attack vector (Value capture, DG lock, ...)
  - Scenario duration (Number of timesteps)

// TODO: @bach check if all current parametrized elements are added
 
# Scenario analytics

For each scenario, a Jupiter Notebook is created and the following information could be provided for each scenario:
- (Add visuals and graph examples)

## Tested scenarios

List of currently completed test scenarios with key test points:

Global System tests
- X runs of Normal Dual Governance operations for 3 months
  - Tests that all parts of the code are working correctly together
  - Tests HP model in general case
  - Check whether DG simulation works well without external pressure
  - Test whether all components of DG proposals, voting, etc. work correctly
- Fund stealing attack on the entire protocol
  - Tests inputs of simple attack scenarios on the system
  - Tests agents' behavior under attack
  - Tests HP model in attack scenario
  - Test of DG state change (Signaling, Ragequit, Cooldown, ...)
 
DG parameter specific tests with key test points:
- Simulation of various user reaction times distributions
  - Testing scenarios with different distribution % of slow, normal and fast users
  - Token ownership per group and their ability to react on proposals in time
- Simulation of various veto signaling and ragequit threshhold parameters
  - Time to signaling
  - Time to ragequit
  - Is there enough active actors to react in time
- Veto Signaling loop attack
  - Number of coordinated users needed to keep this system loop
  - Change of DG states in case of continuous loop
  - Loop duration potential
- Systematic reaction time decrease (>80% of slow reaction actors)
  - What % of slow actors breaks the system from reacting in time on problem proposals
  - What % of active "guardan" funds is needed to keep the system safe from attacks

// TODO: add links to the example notebooks

## Possible questions to be answered

## Scenarios in the pipeline (2024.09.29)

- Proposal impact labels
  - How general system health will be affected if majority of proposals a biased towards specific groups of actors in the system and harms the others
- DAO and stETH misalignment
  - Cost of misaligned decision (e.g. DAO decision goes against community → cost of decision)
- ...
