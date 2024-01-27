import sqlite3
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import typing
import matplotlib.pyplot as plt
import seaborn as sns


con = sqlite3.connect("database.sqlite")

# VISUALIZATION FUNCTIONS


def thousands_formatter(x, pos):
    return f"{int(x/1000)}k"


def millions_formatter(x: float, pos=None, decimals: int = 0) -> str:
    """The two args are the value and tick position"""
    format_string = "{:." + str(decimals) + "f}M"
    return format_string.format(x * 1e-6)


def plot_barchart(df: pd.DataFrame, order: bool = False, percent: bool = True) -> None:
    """
    Plots a barchart with low ink-to-data ratio from a dataframe.
    Annotates the values and percentages (optional).
    Automatically converts large values to millions.
    """

    if order == True:
        df = df.sort_values(by=df.columns[1], ascending=False)

    g = sns.barplot(
        data=df, x=df.columns[0], y=df.columns[1], palette="Greens", width=0.7
    )
    if percent == True:
        total = df[df.columns[1]].sum()
        for index, value in enumerate(df[df.columns[1]]):
            percentage = "{:.1f}%".format(100 * value / total)

            if value > 1e6:
                plt.text(
                    index,
                    value,
                    f"{millions_formatter(value, decimals=1)}\n({percentage})",
                    horizontalalignment="center",
                    verticalalignment="bottom",
                    color="black",
                )

            else:
                plt.text(
                    index,
                    value,
                    f"{int(value)}\n({percentage})",
                    horizontalalignment="center",
                    verticalalignment="bottom",
                    color="black",
                )

    else:
        for index, value in enumerate(df[df.columns[1]]):
            if value > 1e6:
                plt.text(
                    index,
                    value,
                    millions_formatter(value, decimals=1),
                    horizontalalignment="center",
                    verticalalignment="bottom",
                    color="black",
                )
            else:
                plt.text(
                    index,
                    value,
                    str(value),
                    horizontalalignment="center",
                    verticalalignment="bottom",
                    color="black",
                )

    sns.despine(left=True, bottom=True)
    plt.yticks([])
    g.set_xlabel("")
    g.set_ylabel("")


def plot_horiz_barchart(df, names, values, ax=None, decimals=0, order=False):
    if order:
        df = df.sort_values(by=values, ascending=False)

    if names == "index":
        g = sns.barplot(
            data=df, x=values, y=df.index, palette="Greens", width=0.6, ax=ax
        )
    else:
        g = sns.barplot(data=df, x=values, y=names, palette="Greens", width=0.6, ax=ax)

    if decimals == 0:
        for index, value in enumerate(df[values]):
            g.text(value, index + 0.1, "{:,.0f}".format(value).replace(",", "'"))
    elif decimals > 0:
        for index, value in enumerate(df[values]):
            text = round(value, decimals)
            g.text(value, index + 0.1, "{:,}".format(text).replace(",", "'"))

    sns.despine(left=True, bottom=True, ax=ax if ax else plt.gca())
    g.set_xticks([])
    g.set_xlabel("")
    g.set_ylabel("")


def plot_detailed_histogram(series, color="green"):
    bin_edges = np.arange(0.5, series.max() + 1.5)

    sns.histplot(series, bins=bin_edges, color=color)

    plt.xlabel("")
    plt.ylabel("")


# DATA WRANGLING FUNCTIONS


def parse_goal_xml(xml_string, home_team_id, away_team_id):
    if xml_string is None or home_team_id is None or away_team_id is None:
        return []

    root = ET.fromstring(xml_string)
    goals_data = []

    for value in root.findall("value"):
        goal_stats = value.find("stats/goals")
        penalty_stats = value.find("stats/penalties")
        owngoal_stats = value.find("stats/owngoals")

        if goal_stats is None and penalty_stats is None and owngoal_stats is None:
            continue

        team_id = value.findtext("team")
        player1_id = value.findtext("player1")
        player2_id = value.findtext("player2")
        elapsed_time = value.findtext("elapsed")
        goal_subtype = value.findtext("subtype")

        # Determine goal type
        if goal_stats is not None:
            goal_type = "shot"
        elif penalty_stats is not None:
            goal_type = "penalty"
        elif owngoal_stats is not None:
            goal_type = "owngoal"
            player1_id = "-7"
            # Switch the team ID to the opponent
            if team_id == str(home_team_id):
                team_id = str(away_team_id)
            else:
                team_id = str(home_team_id)

        goal_data = {
            "team_id": team_id,
            "player_id": player1_id,
            "assist_id": player2_id,
            "type": goal_type,
            "subtype": goal_subtype,
            "minute": elapsed_time,
        }

        goals_data.append(goal_data)

    return goals_data


def append_player_names(df, con):
    """
    Appends a 'player_name' column to the input dataframe based on 'player_id'.
    :param df: The dataframe containing 'player_id' column.
    :param con: Database connection object.
    :return: Dataframe with an appended 'player_name' column.
    """

    df["player_id"] = df["player_id"].astype("int64")

    unique_player_ids = df["player_id"].unique().tolist()
    player_id_str = ",".join(map(str, unique_player_ids))

    query_players = f"SELECT player_api_id, player_name FROM Player WHERE player_api_id IN ({player_id_str})"
    players_df = pd.read_sql_query(query_players, con=con)

    players_df["player_api_id"] = players_df["player_api_id"].astype("int64")

    # Merge with the input dataframe to get player names
    df = pd.merge(
        df, players_df, left_on="player_id", right_on="player_api_id", how="left"
    ).drop("player_api_id", axis=1)

    return df


def append_team_names(df, con):
    """
    Appends a 'player_name' column to the input dataframe based on 'player_id'.
    :param df: The dataframe containing 'player_id' column.
    :param con: Database connection object.
    :return: Dataframe with an appended 'player_name' column.
    """

    df["team_id"] = df["team_id"].astype("int64")

    unique_ids = df["team_id"].unique().tolist()
    team_id_str = ",".join(map(str, unique_ids))

    query_players = f"SELECT team_api_id, team_long_name FROM Team WHERE team_api_id IN ({team_id_str})"
    teams_df = pd.read_sql_query(query_players, con=con)

    teams_df["team_api_id"] = teams_df["team_api_id"].astype("int64")

    # Merge with the input dataframe to get player names
    df = pd.merge(
        df, teams_df, left_on="team_id", right_on="team_api_id", how="left"
    ).drop("team_api_id", axis=1)

    return df
