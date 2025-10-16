import time
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx

from src.uni_sync.model import UniSyncModel


def visualize_leader_election(num_agents: int = 5, max_steps: int = 30) -> None:
    model = UniSyncModel(num_agents)

    G = model.grid.G
    pos = nx.circular_layout(G)

    plt.ion()
    fig, ax = plt.subplots(figsize=(6, 6))

    # Map node id to agent for color/labeling
    node_to_agent = {agent.unique_id: agent for agent in model.agents}

    for step in range(max_steps):
        ax.clear()
        colors = []
        labels = {}

        for node in G.nodes:
            agent = node_to_agent.get(node)
            if agent is not None:
                labels[node] = (
                    str(node)
                    + f"(L: {agent.leader if agent.leader is not None else -1})"
                )

                if agent.leader is not None:
                    if agent.leader == agent.unique_id:
                        colors.append("gold")  # Leader
                    else:
                        colors.append("lightgreen")  # Decided
                else:
                    colors.append("skyblue")  # Undecided

            else:
                labels[node] = str(node)
                colors.append("gray")  # No agent, shouldn't happen

        nx.draw_networkx(
            G,
            pos=pos,
            ax=ax,
            node_color=colors,
            with_labels=True,
            labels=labels,
            node_size=1900,
            font_color="black",
        )

        highlighted_edges: list[tuple[int, int]] = []
        edge_labels: dict[tuple[int, int], Any] = {}

        for agent_rec_id, messages in model.current_round_messages.items():
            for message in messages:
                sender_id = message["sender_id"]
                highlighted_edges.append((sender_id, agent_rec_id))
                edge_labels[(sender_id, agent_rec_id)] = message["payload"]

        # Draw highlighted edges (red and thicker)
        if highlighted_edges:
            _ = nx.draw_networkx_edges(
                G,
                pos,
                edgelist=highlighted_edges,
                edge_color="blue",
                width=2,
                ax=ax,
            )

            _ = nx.draw_networkx_edge_labels(
                G,
                pos,
                edge_labels=edge_labels,
                font_color="blue",
                font_size=10,
                ax=ax,
                label_pos=0.5,
                rotate=False,
            )

        ax.set_title(f"Step {step}")

        if model.all_agents_finished():
            break

        plt.pause(2.0)
        model.step()

    plt.ioff()
    plt.show()


if __name__ == "__main__":
    num_agents = 5
    max_steps = 4 * num_agents + 1
    visualize_leader_election(num_agents=num_agents, max_steps=max_steps)
