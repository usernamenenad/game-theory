import matplotlib.pyplot as plt
import networkx as nx
import time
from src.uni_sync.model import UniSyncModel


def visualize_leader_election(num_agents=5, max_steps=30, pause=1.0):
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
                labels[node] = str(node)
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
            node_size=800,
            font_color="black",
        )
        ax.set_title(f"Step {step}")
        plt.pause(pause)

        if model.all_agents_finished():
            break
        model.step()

    plt.ioff()
    plt.show()


if __name__ == "__main__":
    visualize_leader_election(num_agents=5, max_steps=30, pause=1.0)
