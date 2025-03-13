import csv

import numpy as np


def assign_labels_by_funds_threshold(funds_threshold: int, main_label: str, counter_label: str):
    labeled_addresses: dict[str, str] = dict()

    with open("data/stETH token distribution  - stETH+wstETH holders.csv", mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        line_count = 0

        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                continue

            total_funds = int(float(row["total"]))

            if total_funds >= funds_threshold:
                labeled_addresses[row["address"]] = main_label
            else:
                labeled_addresses[row["address"]] = counter_label

    return labeled_addresses


def assign_labels_by_percentage(
    main_label: str = "Decentralized",
    counter_label: str = "Centralized",
) -> callable:
    """
    Creates a function that assigns labels to actors based on a percentage.

    Args:
        anti_decentralized_percentage: Float between 0 and 100
        decentralized_label: Label for decentralized actors
        anti_decentralized_label: Label for anti-decentralized actors

    Returns:
        Function that takes actor addresses and assigns labels
    """

    def labeling_function(
        existing_labels: np.ndarray,
        reaction_mask: np.ndarray,
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
        determining_factor: int = 0,
    ) -> np.ndarray:
        from model.utils.seed import get_rng

        rng = get_rng()

        labels = existing_labels.copy()
        labels[reaction_mask] = main_label

        eligible_indices = np.where(reaction_mask)[0]

        num_anti = int(len(eligible_indices) * (determining_factor / 100))
        anti_indices = rng.choice(eligible_indices, size=num_anti, replace=False)

        labels[anti_indices] = counter_label

        return labels

    return labeling_function


def assign_labels_by_funds_threshold_active_actors(
    main_label: str = "Retail",
    counter_label: str = "Institutional",
) -> callable:
    """
    Creates a function that assigns labels to actors based on their total funds.

    Args:
        funds_threshold: Threshold in ETH (will be converted to Wei internally)
        main_label: Label for actors below threshold
        counter_label: Label for actors above threshold

    Returns:
        Function that takes actor addresses and assigns labels based on funds
    """

    from specs.utils import ether_base

    def labeling_function(
        existing_labels: np.ndarray,
        reaction_mask: np.ndarray,
        stETH_amounts: np.ndarray,
        wstETH_amounts: np.ndarray,
        determining_factor: int = 0,
    ) -> np.ndarray:
        labels = existing_labels.copy()
        labels[reaction_mask] = main_label

        total_funds = stETH_amounts + wstETH_amounts
        threshold_in_wei = determining_factor * ether_base
        institutional_mask = (total_funds >= threshold_in_wei) & reaction_mask

        labels[institutional_mask] = counter_label

        return labels

    return labeling_function
