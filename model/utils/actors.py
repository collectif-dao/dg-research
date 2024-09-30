from typing import List, Set

from model.actors.actor import BaseActor
from model.actors.token_holders.coordinated_stETH_attacker import CoordinatedStETHAttackerActor
from model.actors.token_holders.defender_actor import StETHDefenderActor
from model.actors.token_holders.single_stETH_attacker import SingleStETHAttackerActor
from model.actors.token_holders.stETH_holder_actor import StETHHolderActor
from model.types.scenario import Scenario
from model.utils.seed import get_rng


def determine_actor_health(scenario: Scenario, mean_health=50, std_dev_health=20):
    rng = get_rng()

    health_value = int(rng.normal(mean_health, std_dev_health))
    health = max(1, min(100, health_value))

    return health


def determine_actor_types(scenario: Scenario, address: str, attackers: Set[str], defenders: Set[str]):
    rng = get_rng()

    if address in attackers:
        if scenario == Scenario.CoordinatedAttack:
            return CoordinatedStETHAttackerActor()
        elif scenario == Scenario.SingleAttack:
            return SingleStETHAttackerActor()
        elif scenario == Scenario.VetoSignallingLoop:
            return CoordinatedStETHAttackerActor()
    elif address in defenders:
        return StETHDefenderActor()
    else:
        match scenario:
            case Scenario.HappyPath:
                return StETHHolderActor()

            case Scenario.SingleAttack:
                actors_distribution = rng.normal(0, 1)

                if actors_distribution >= 3:
                    return SingleStETHAttackerActor()
                else:
                    return StETHHolderActor()

            case Scenario.CoordinatedAttack:
                actors_distribution = rng.normal(0, 1)

                if actors_distribution >= 3:
                    return CoordinatedStETHAttackerActor()
                else:
                    return StETHHolderActor()

            case Scenario.VetoSignallingLoop:
                actors_distribution = rng.normal(0, 1)

                if actors_distribution >= 3:
                    return CoordinatedStETHAttackerActor()
                else:
                    return StETHHolderActor()


def get_coordinated_attackers(actors: List[BaseActor], coordinated_attacker_addresses: Set[str]) -> List[BaseActor]:
    return [actor for actor in actors if actor.address in coordinated_attacker_addresses]
