import mesa
import networkx as nx

from src.uni_sync.agent import UniSyncAgent
from src.uni_sync.types import Message


class UniSyncModel(mesa.Model):
    def __init__(self, N: int) -> None:
        super().__init__()

        self.num_agents = N

        graph = nx.DiGraph()
        for i in range(self.num_agents):
            graph.add_node(i)

        self.grid = mesa.space.NetworkGrid(graph)

        for i in range(self.num_agents):
            agent = UniSyncAgent(self)
            agent.unique_id = i  # Ensure unique_id matches node id
            self.agents.add(agent)
            self.grid.place_agent(agent, i)

        for i in range(self.num_agents):
            source_agent_idx = i
            target_agent_idx = (i + 1) % self.num_agents

            self.grid.G.add_edge(source_agent_idx, target_agent_idx)
            self.agents[source_agent_idx].successor = self.agents[target_agent_idx]  # type: ignore

        self.current_round_messages: dict[int, list[Message]] = {
            agent.unique_id: [] for agent in self.agents
        }

        starter_agent = self.random.choice(self.agents)
        starter_agent.start_protocol()  # type: ignore

        self.datacollector = mesa.DataCollector(
            agent_reporters={
                "Phase": "phase",
                "Random number": "N_rand",
                "Leader": "leader",
            }
        )

    def buffer_message(self, agent: UniSyncAgent, message: Message):
        self.current_round_messages[agent.unique_id].append(message)

    def step(self) -> None:
        for agent in self.agents:
            agent.inbox.extend(self.current_round_messages[agent.unique_id])  # type: ignore
            self.current_round_messages[agent.unique_id].clear()

        self.agents.do("step")
        self.datacollector.collect(self)

    def all_agents_finished(self) -> None:
        """Check if all agents have chosen a leader or failed."""

        return all(agent.leader is not None for agent in self.agents)  # type: ignore
