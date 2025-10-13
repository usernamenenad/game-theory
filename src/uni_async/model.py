import random
import mesa
import networkx as nx
from src.uni_async.agent import UniAsyncAgent
from src.uni_async.network import UniAsyncNetwork


class UniAsyncModel(mesa.Model):
    def __init__(self, N: int, max_message_delay: int = 5) -> None:
        super().__init__()

        self.num_agents = N
        self.ticks = 0
        self.random_gen = random.Random()
        self.abort_flag = False

        def delay_fcn(_payload: dict) -> int:
            return self.random_gen.randint(1, max_message_delay)

        self.network = UniAsyncNetwork(self, delay_fcn)
        self.agent_list: list[UniAsyncAgent] = []

        graph = nx.DiGraph()
        for i in range(self.num_agents):
            graph.add_node(i)

        self.grid = mesa.space.NetworkGrid(graph)

        for i in range(self.num_agents):
            a = UniAsyncAgent(self)
            a.unique_id = i
            self.agent_list.append(a)
            self.grid.place_agent(a, i)

        for i in range(self.num_agents):
            a = self.agent_list[i]
            a.successor = self.agent_list[(i + 1) % self.num_agents]
            a.predecessor = self.agent_list[(i - 1) % self.num_agents]

        starter = random.choice(self.agent_list)
        starter.start_protocol()

        self.datacollector = mesa.DataCollector(
            agent_reporters={"Leader": "leader", "Phase": "phase"}
        )

    def step(self) -> None:
        if self.abort_flag:
            return
        self.network.step()
        for a in self.agent_list:
            a.step()
        self.datacollector.collect(self)
        self.ticks += 1

    def all_finished(self) -> bool:
        if self.abort_flag:
            return True
        return all(a.leader is not None for a in self.agent_list)
