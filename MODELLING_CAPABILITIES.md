# Model Capabilities

This document outlines the key simulation capabilities of the model developed for Lido Dual Governance. These capabilities allow to understand, which elements of DG are now parametrized for simulations, what type of questions the model can take, and which answers it can provide.

## Main simulation pathways 

The model provides a framework to create simulation scenarios to validate DG under different conditions. In general, there are two major scenario groups:
- Regular system behavior - DG life without major proposals or attacks
- Irregular system behavior - specific cases like attacks, DG bottlenecks, significant market fluctuations, external hacks, etc.

## Current model state

At the moment, the model is capable of simulating the following groups of scenarios:
- Normal Dual Governance operations (multiple months of DG life with random proposal generated for DG)
- Attacks on the entire protocol (predefined attacking proposal on the Lido Protocol)
- Testing specific parameters of DG (multiple Monte-Carlo simulations or attacks to test different values of isolated DG parameters)

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
  - Scenario duration (short, long, ...)
 
## Extractable analytics

For each scenario, a Jupiter Notebook is created and the following information could be provided for each scenario:
- (Add visuals and graph examples)

## Possible questions to be answered

Lorem Ipsum
