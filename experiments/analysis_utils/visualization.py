import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm

from model.types.actors import get_attacker_types


def add_proposal_data_to_timeplot(ax: plt.Axes,
                                  proposal_df: pd.DataFrame,
                                  lines: tuple[int, int, int, int, int] = (1, 1, 1, 1, 1)
                                  ) -> None:
    line_types = [
        ((0, (1, 20)), "submission"),
        ((0, (1, 10)), "earliest possible execution"),
        ("dotted", "schedule"),
        ((0, (5, 10)), "possible execution time"),
        ("-", "actual execution"),
    ]

    ylim = ax.get_ylim()
    colors = cm.rainbow(np.linspace(0, 1, len(proposal_df)))

    used_line_types = []

    for i, proposal_id in enumerate(proposal_df.index):
        proposal = proposal_df.loc[proposal_id]

        submission_timestep = proposal.submittedAt
        if lines[0]:
            submission_time_line = ax.plot(
                np.repeat(submission_timestep, 2), [0, ylim[1]], linestyle=line_types[0][0], c=colors[i]
            )
            used_line_types.append(0)

        earliest_execution_timestep = submission_timestep + 5 * 24 / 3

        if lines[1]:
            early_execution_time_line = ax.plot(
                np.repeat(earliest_execution_timestep, 2), [0, ylim[1]], linestyle=line_types[1][0], c=colors[i]
            )
            used_line_types.append(1)

        schedule_timestep = proposal.scheduledAt
        if schedule_timestep > submission_timestep:
            if lines[2]:
                schedule_time_line = ax.plot(
                    np.repeat(schedule_timestep, 2), [0, ylim[1]], linestyle=line_types[2][0], c=colors[i]
                )
                used_line_types.append(2)
            possible_execution_timestep = schedule_timestep + 3 * 24 / 3
            if lines[3]:
                possible_execution_time_line = ax.plot(
                    np.repeat(possible_execution_timestep, 2), [0, ylim[1]], linestyle=line_types[3][0], c=colors[i]
                )
                used_line_types.append(3)

        execution_timestep = proposal.executedAt
        if execution_timestep > schedule_timestep:
            if lines[4]:
                real_execution_time_line = ax.plot(
                    np.repeat(execution_timestep, 2), [0, ylim[1]], linestyle=line_types[4][0], c=colors[i]
                )
                used_line_types.append(4)
        ax.set_ylim(ylim)

    for i, color in enumerate(colors):
        ax.plot([], [], c=color, label=f"Proposal {proposal_df.proposal_id.iloc[i]}")
    for i in used_line_types:
        linestyle, label = line_types[i]
        ax.plot([], [], linestyle=linestyle, c="gray", label=label)


def plot_reaction_speed_distribution(
    start_data_df: pd.DataFrame,
    run_id: int,
    ax: plt.Axes | None = None,
    title: str = "Actors reaction speed"
) -> plt.Axes:
    """
    Plot pie chart of actor reaction speed distribution for a single run
    
    Args:
        start_data_df: DataFrame containing start data for different runs
        run_id: ID of the run to plot
        ax: Optional matplotlib axes to plot on
        title: Plot title
        
    Returns:
        matplotlib axes with the plot
    """
    if ax is None:
        _, ax = plt.subplots()
    
    # Get data for specific run
    run_data = start_data_df[start_data_df["run_id"] == run_id].copy()
    
    # Calculate attackers total
    run_data["Attackers"] = run_data[[actor_type.name for actor_type in get_attacker_types()]].sum(axis=1)

    # Prepare data for plotting
    cols = ["Slow", "Normal", "Quick", "Attackers"]
    values = np.array(run_data[cols])[0]
    # Subtract attackers from Quick actors as they're included there
    values[2] = values[2] - values[3]

    # Remove attackers if there are none
    if values[3] == 0:
        cols.pop()
        values = values[:-1]

    n_actors = run_data["n_actors"].iloc[0]

    # Format function for labels
    def fmt(x: float) -> str:
        return f"{int(x.round())}% ({int((x * n_actors / 100).round())})"

    ax.pie(values, labels=cols, autopct=fmt)
    ax.set_title(title)
    
    return ax

def plot_token_distribution(
    timestep_data_df: pd.DataFrame,
    run_id: int,
    ax: plt.Axes | None = None,
    title: str = "Tokens by reaction speed"
) -> plt.Axes:
    """
    Plot pie chart of token distribution across actor reaction speeds for a single run
    
    Args:
        timestep_data_df: DataFrame containing timestep data for different runs
        run_id: ID of the run to plot
        ax: Optional matplotlib axes to plot on
        title: Plot title
        
    Returns:
        matplotlib axes with the plot
    """
    if ax is None:
        _, ax = plt.subplots()
    
    # Get data for specific run at timestep 1
    timestep_data_df_run = timestep_data_df[timestep_data_df["run_id"] == run_id]
    timestep_data_df_run_start = timestep_data_df_run[timestep_data_df_run["timestep"] == 1].copy()
    
    # Calculate attackers total
    attacker_labels = [actor_type.name for actor_type in get_attacker_types()]
    timestep_data_df_run_start["balance_Attackers"] = sum(
        timestep_data_df_run_start[f"balance_{label}"] for label in attacker_labels
    )

    # Prepare data for plotting
    cols = ["Slow", "Normal", "Quick", "Attackers"]
    values = np.array(timestep_data_df_run_start[[f"balance_{col}" for col in cols]])[0]
    values[2] = values[2] - values[3]
    
    # Remove attackers if there are none
    if values[3] == 0:
        cols.pop()
        values = values[:-1]

    initial_tokens = timestep_data_df_run_start["actors_total_balance"].iloc[0]
    
    # Format function for labels
    def fmt(x: float) -> str:
        return f"{int(x.round())}% ({x * initial_tokens / 100:.2f})"

    ax.pie(values, labels=cols, autopct=fmt)
    ax.set_title(title)
    
    return ax