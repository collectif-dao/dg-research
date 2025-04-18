from pathlib import Path

import pandas as pd

from specs.utils import ether_base

path_to_simulations = Path("experiments/results/simulations/")


def read_directory(path: Path, drop_duplicates: bool = False, pass_directory_name: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    proposal_df_list, start_data_df_list, timestep_data_df_list = [], [], []
    for i, p_to_tables in enumerate(path.iterdir()):
        proposals_p = p_to_tables.joinpath("proposals_data.parquet")
        start_data_p = p_to_tables.joinpath("common_data.parquet")
        timestep_data_p = p_to_tables.joinpath("timestep_data.parquet")
        if not proposals_p.exists() or not start_data_p.exists() or not timestep_data_p.exists():
            # print(p_to_tables)
            continue
        start_data_df = pd.read_parquet(start_data_p)
        proposals_df = pd.read_parquet(proposals_p)
        timestep_data_df = pd.read_parquet(timestep_data_p)

        if pass_directory_name:
            start_data_df["directory_name"] = p_to_tables.name
            timestep_data_df["directory_name"] = p_to_tables.name
            proposals_df["directory_name"] = p_to_tables.name

        start_data_df_list.append(start_data_df)
        proposal_df_list.append(proposals_df)
        timestep_data_df_list.append(timestep_data_df)

    proposal_df_full = pd.concat(proposal_df_list)
    start_data_df_full = pd.concat(start_data_df_list)
    timestep_data_df_full = pd.concat(timestep_data_df_list)

    if drop_duplicates:
        start_data_df_full = start_data_df_full.drop_duplicates()
        proposal_df_full = proposal_df_full.drop_duplicates(
            subset=proposal_df_full.drop(columns=["proposal_effects_labels", "proposal_effects_damages"]).columns.tolist())
        timestep_data_df_full = timestep_data_df_full.drop_duplicates()

    postprocess_start_data(start_data_df_full)
    postprocess_timestep_data(timestep_data_df_full)
    postprocess_proposal_data(proposal_df_full)

    set_run_id(proposal_df_full, start_data_df_full, timestep_data_df_full)
    start_data_df_full = add_attacker_share(timestep_data_df_full, start_data_df_full)

    return proposal_df_full, start_data_df_full, timestep_data_df_full


def set_run_id(*dfs: pd.DataFrame) -> None:
    hash_to_run_id = {sim_hash: i for i, sim_hash in enumerate(dfs[0]["simulation_hash"].unique())}
    for df in dfs:
        df["run_id"] = df["simulation_hash"].map(hash_to_run_id)


def postprocess_start_data(start_data_df: pd.DataFrame) -> None:
    start_data_df["first_seal_rage_quit_support"] /= ether_base
    start_data_df["second_seal_rage_quit_support"] /= ether_base


def postprocess_timestep_data(timestep_data_df: pd.DataFrame) -> None:
    initial_balances = (
        timestep_data_df[timestep_data_df["timestep"] == 1].groupby("simulation_hash")["actors_total_balance"].first()
    )
    initial_health = (
        timestep_data_df[timestep_data_df["timestep"] == 1].groupby("simulation_hash")["actors_total_health"].first()
    )

    # Map initial balances to all timesteps of corresponding runs
    run_initial_balances = timestep_data_df["simulation_hash"].map(initial_balances)
    run_initial_health = timestep_data_df["simulation_hash"].map(initial_health)

    # Calculate relative balance
    timestep_data_df["actors_total_balance_relative"] = timestep_data_df["actors_total_balance"] / run_initial_balances
    timestep_data_df["actors_total_locked_relative"] = timestep_data_df["actors_total_locked"] / run_initial_balances
    timestep_data_df["actors_total_health_relative"] = timestep_data_df["actors_total_health"] / run_initial_health


def postprocess_proposal_data(proposal_df: pd.DataFrame) -> None:
    pass


def add_attacker_share(timestep_data_df: pd.DataFrame, start_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate and add attacker_share column to start_data_df based on initial balances and attacker funds.

    Args:
        timestep_data_df: DataFrame containing timestep data with actors_total_balance
        start_data_df: DataFrame containing start data with attacker_funds

    Returns:
        Modified start_data_df with new attacker_share column
    """
    # Get initial balances (timestep=1) for each run
    initial_balances = timestep_data_df[timestep_data_df["timestep"] == 1][["run_id", "actors_total_balance"]]
    initial_balances = initial_balances.rename(columns={"actors_total_balance": "initial_total_balance"})

    # Merge and calculate attacker share
    start_data_df = start_data_df.merge(initial_balances, on="run_id")
    start_data_df["attacker_share"] = start_data_df["attacker_funds"] / start_data_df["initial_total_balance"]

    return start_data_df

def clean_timesteps_ragequit_loop(timestep_data_df: pd.DataFrame) -> pd.DataFrame:
    # Initialize a list to store the cleaned data
    cleaned_data = []

    # Group by 'run_id'
    for run_id, group in timestep_data_df.groupby("run_id"):
        # Reset index for the group
        group = group.reset_index(drop=True)

        # Initialize variables to track state
        current_state = None
        normal_episode_count = 0
        cooldown_episode_count = 0
        cleaned_group = []

        # Iterate over the rows in the group
        for index, row in group.iterrows():
            if row["dg_state_name"] != current_state:
                # State change detected
                current_state = row["dg_state_name"]
                if current_state == "VetoCooldown":
                    cooldown_episode_count += 1
                if current_state == "Normal":
                    normal_episode_count += 1
                if (cooldown_episode_count >= 1) or (normal_episode_count >= 2):
                    # Stop processing after the second Normal episode
                    break

            # Append the row to cleaned data
            cleaned_group.append(row)

        # Extend the cleaned data with the current group
        cleaned_data.extend(cleaned_group)

    # Convert cleaned data to a DataFrame
    return pd.DataFrame(cleaned_data)