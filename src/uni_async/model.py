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

        self.starter: UniAsyncAgent | None = None
        self.received_leader_reports: set[int] = set()

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
        self.starter = starter
        starter.start_protocol()

        self.datacollector = mesa.DataCollector(
            agent_reporters={"Leader": "leader", "Phase": "phase"}
        )

    def register_leader_report(self, agent_id: int) -> None:
        self.received_leader_reports.add(agent_id)
        print(f"[Model] Starter received leader report from Agent {agent_id}")

    def step(self) -> None:
        if self.abort_flag:
            return

        self.network.step()
        for a in self.agent_list:
            a.step()

        self.datacollector.collect(self)
        self.ticks += 1

        if self.all_finished():
            if self.abort_flag:
                print(
                    f"[Model] ❌ Consensus aborted after {self.ticks} ticks — "
                    f"cheating was detected and protocol halted."
                )
            else:
                print(
                    f"[Model] ✅ Consensus complete after {self.ticks} ticks. "
                    f"All {len(self.received_leader_reports)} leader reports received by starter "
                    f"(Agent {self.starter.unique_id})."
                )

    def all_finished(self) -> bool:
        if self.abort_flag:
            return True

        if not self.starter:
            return False

        return len(self.received_leader_reports) == self.num_agents
