from matplotlib import pyplot as plt
from pandas import DataFrame
from pandas._typing import Scalar

from specs.dual_governance.state import State


def create_bar_charts(post_processing, *charts):
    num_charts = len(charts)
    fig, axs = plt.subplots(1, num_charts, figsize=(7.5 * num_charts, 6))

    if num_charts == 1:
        axs = [axs]  # Ensure axs is always a list

    for i, (attributes, labels, title, ylabel) in enumerate(charts):
        values = [getattr(post_processing, attr).tail(1).values[0] for attr in attributes]
        axs[i].bar(labels, values)
        axs[i].set_title(title)
        axs[i].set_xlabel("")
        axs[i].set_ylabel(ylabel)

    plt.tight_layout()
    plt.show()


def monte_carlo_plot(df, aggregate_dimension, x, y, runs):
    mean_df, median_df, std_df, min_df = aggregate_runs(df, aggregate_dimension)
    plt.figure(figsize=(10, 6))
    for r in range(1, runs + 1):
        legend_name = "Run " + str(r)
        plt.plot(df[df.simulation == r][x], df[df.simulation == r][y], label=legend_name)
    plt.plot(mean_df[x], mean_df[y], label="Mean", color="black")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlabel(x)
    plt.ylabel(y)
    title_text = "Performance of " + y + " over " + str(runs) + " Monte Carlo Runs"
    plt.title(title_text)


def state_plot(df, x, y, run):
    states = df[df.simulation == run][y].map(lambda r: State(r).name)
    states.value_counts().plot(kind="bar").set_title("DG states time")
    plt.figure(figsize=(10, 6))
    plt.plot(df[df.simulation == run][x], states)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title("DG States")
    plt.show()


def aggregate_runs(df: DataFrame, aggregate_dimension: Scalar):
    df_copy = df.copy()
    df_copy = df_copy.drop(columns=["current_time"])
    mean_df = df_copy.groupby(aggregate_dimension).mean(numeric_only=True).reset_index()
    median_df = df_copy.groupby(aggregate_dimension).median(numeric_only=True).reset_index()
    std_df = df_copy.groupby(aggregate_dimension).std(numeric_only=True).reset_index()
    min_df = df_copy.groupby(aggregate_dimension).min(numeric_only=True).reset_index()

    mean_df.loc[:, "current_time"] = df["current_time"]
    median_df.loc[:, "current_time"] = df["current_time"]
    std_df.loc[:, "current_time"] = df["current_time"]
    min_df.loc[:, "current_time"] = df["current_time"]
    return mean_df, median_df, std_df, min_df
