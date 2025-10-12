import random
from typing import Any

import mesa
import networkx as nx

from src.uni_async.agent import UniAsyncAgent
from src.uni_async.network import UniAsyncNetwork


class UniAsyncModel(mesa.Model):
    def __init__(
        self,
        N: int,
        max_message_delay: int = 5,
    ) -> None:
        super().__init__()

        self.num_agents = N
        self.ticks = 0
        self.random_gen = random.Random()

        def delay_fcn(_payload: dict[str, Any]) -> int:
            return self.random_gen.randint(1, max_message_delay)

        self.network = UniAsyncNetwork(self, delay_fcn)

        graph = nx.DiGraph()
        for i in range(self.num_agents):
            graph.add_node(i)

        self.grid = mesa.space.NetworkGrid(graph)

        for i in range(self.num_agents):
            agent = UniAsyncAgent(self)
            self.agents.add(agent)

            self.grid.place_agent(agent, i)

        for i in range(self.num_agents):
            source_agent_idx = i
            target_agent_idx = (i + 1) % self.num_agents

            self.grid.G.add_edge(source_agent_idx, target_agent_idx)
            self.agents[source_agent_idx].successor = self.agents[target_agent_idx]  # type: ignore

        self.datacollector = mesa.DataCollector(
            agent_reporters={"Leader": "leader", "Phase": "phase"}
        )

    def step(self) -> None:
        self.agents.do("step")
        self.datacollector.collect(self)
