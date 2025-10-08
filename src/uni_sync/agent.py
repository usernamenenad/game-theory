import random
from typing import Self

import mesa

from src.uni_sync.types import Message, MessageType


class UniSyncAgent(mesa.Agent):
    PUNISH_STATE = None  # If something goes wrong, no leader should be chosen.

    def __init__(self, model: mesa.Model) -> None:
        super().__init__(model)

        self.leader: int | None = None

        self.highest = -1  # Highest message originator seen.
        self.phase = 0  # Current protocol phase.
        self.count = 0  # Message trip count.
        self.id_set: set[int] = set()  # All agent ids seen.
        self.N_rand: int = -1
        self.all_N_rand: dict[int, int] = {}  # Received random numbers.

        self.inbox: list[Message] = []
        self.successor: Self | None = None

    def start_protocol(self) -> None:
        """
        Corresponds to `UponWaking` method.
        """

        if self.phase != 0:
            return

        print(f"[Agent {self.unique_id}]: Waking up and starting protocol.")

        self.highest = self.unique_id
        self.count = self.model.num_agents  # type: ignore
        self.phase = 1
        self.id_set = {self.unique_id}

        first_collect_message: Message = {
            "message_type": MessageType.COLLECT,
            "sender_id": self.unique_id,
            "payload": self.id_set,
        }

        self.send_to_successor(first_collect_message)

    def send_to_successor(self, message: Message) -> None:
        """Sends a message to agent's successor in the ring."""

        if self.successor:
            self.model.buffer_message(self.successor, message)  # type: ignore

    def step(self) -> None:
        """
        Executes one step of the protocol for an agent.
        This is a synchronous operation, meaning all agents
        will execute this at the same time.
        """

        if self.leader is not None:
            return

        if self.phase > 0:
            self.count -= 1

        messages: list[Message] = self.inbox.copy()
        self.inbox.clear()

        for message in messages:
            message_type = message["message_type"]
            sender_id = message["sender_id"]
            payload = message["payload"]

            match message_type:
                case MessageType.COLLECT:
                    if self.phase == 0:
                        """
                        Sanity check. Agent is joining the protocol here.
                        Represents `UponWaking`, 
                        but the agent itself is not the originator.
                        """

                        self.phase = 1
                        self.highest = sender_id
                        self.id_set = payload | {self.unique_id}
                        self.count = self.model.num_agents  # type: ignore

                        first_collect_message: Message = {
                            "message_type": MessageType.COLLECT,
                            "sender_id": self.highest,
                            "payload": self.id_set,
                        }
                        self.send_to_successor(first_collect_message)

                    if self.phase == 1 and sender_id > self.highest:
                        """
                        FIRST MESSAGE PASS.
                        If the agent protocol is in the phase 1 but
                        the agent is not the message originator,
                        it just passes on the message to its' successor.
                        """

                        self.highest = sender_id
                        self.id_set = payload | {self.unique_id}
                        self.count = self.model.num_agents  # type: ignore

                        new_collect_message: Message = {
                            "message_type": MessageType.COLLECT,
                            "sender_id": self.highest,
                            "payload": self.id_set,
                        }
                        self.send_to_successor(new_collect_message)

                    elif sender_id == self.highest and self.unique_id == self.highest:
                        """
                        First round trip of the message, 
                        originator got its' message back.
                        Originator checks if the message round trip number
                        is equal to number of agents
                        and starts phase 2.
                        """

                        if not (
                            len(payload) == self.model.num_agents  # type: ignore
                            and self.phase == 1
                            and self.count == 0
                        ):
                            self.leader = UniSyncAgent.PUNISH_STATE
                            return

                        self.phase = 2
                        self.id_set = payload.copy()
                        self.count = self.model.num_agents  # type: ignore

                        setup_message: Message = {
                            "message_type": MessageType.SETUP,
                            "sender_id": self.unique_id,
                            "payload": self.id_set,
                        }
                        self.send_to_successor(setup_message)
                        continue

                case MessageType.SETUP:
                    """
                    Agents check if the round trip of their 
                    message is equal to number of agents.
                    Also, the sender of the message should be
                    the same as highest agent has seen (a.k.a. originator should've sent the message).
                    """

                    if self.phase > 1:
                        continue

                    if not (
                        sender_id == self.highest
                        and self.phase == 1
                        and self.count == 0
                    ):
                        self.leader = UniSyncAgent.PUNISH_STATE
                        return

                    self.phase = 2
                    self.id_set = payload.copy()
                    self.count = self.model.num_agents  # type: ignore
                    self.send_to_successor(message)
                    continue

                case MessageType.RANDOM:
                    """
                    Invokes sending a random number from message
                    originator to successor.
                    """

                    if sender_id not in self.all_N_rand:
                        self.all_N_rand[sender_id] = payload
                        self.send_to_successor(message)
                        continue

        if self.phase == 2 and self.count == 0:
            """
            Originator starts the phase 3 of the protocol. 
            Picks a random number and sends it as a separate message.
            """

            self.phase = 3
            self.count = self.model.num_agents  # type: ignore

            self.N_rand = random.randint(0, self.model.num_agents - 1)  # type: ignore
            self.all_N_rand[self.unique_id] = self.N_rand

            rand_message: Message = {
                "message_type": MessageType.RANDOM,
                "sender_id": self.unique_id,
                "payload": self.N_rand,
            }

            self.send_to_successor(rand_message)
            return

        if self.phase == 3 and self.count == 0:
            """
            All agents pick a leader. If any of the agents
            don't get as many random numbers as there are agents, they hault.
            """

            if len(self.all_N_rand) != self.model.num_agents:  # type: ignore
                self.leader = UniSyncAgent.PUNISH_STATE
                return

            total_sum = sum(self.all_N_rand.values())
            N = total_sum % len(self.all_N_rand)

            self.leader = int(sorted(list(self.id_set), reverse=True)[N])
