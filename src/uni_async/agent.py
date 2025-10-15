from collections import deque
import random
import mesa
from src.uni_async.types import AsyncMessageType


class UniAsyncAgent(mesa.Agent):
    PUNISH_STATE = None

    def __init__(self, model: mesa.Model) -> None:
        super().__init__(model)
        self.leader: int | None = None
        self.highest = -1
        self.phase = 0
        self.id_set: set[int] = set()
        self.N_rand: int = -1
        self.commit_from_predecessor: int | None = None

        self.inbox: deque[dict] = deque()
        self.predecessor: "UniAsyncAgent" | None = None
        self.successor: "UniAsyncAgent" | None = None

    def send_to_successor(self, payload: dict) -> None:
        if self.successor:
            self.model.network.send(self.unique_id, self.successor.unique_id, payload)

    def abort_protocol(self, expected: int, revealed: int) -> None:
        print(
            f"[Agent {self.unique_id}] detected cheating by predecessor! "
            f"Committed {expected}, revealed {revealed}"
        )
        self.model.abort_flag = True
        self.leader = UniAsyncAgent.PUNISH_STATE

    def start_protocol(self) -> None:
        if self.phase != 0:
            return
        print(f"[Agent {self.unique_id}] starts protocol.")

        self.highest = self.unique_id
        self.phase = 1
        self.id_set.add(self.unique_id)

        self.send_to_successor(
            {
                "message_type": AsyncMessageType.COLLECT,
                "sender_id": self.unique_id,
                "content": {"id_set": self.id_set},
            }
        )

    def step(self) -> None:
        """Handle one tick of this agent."""
        if self.model.abort_flag:
            self.leader = UniAsyncAgent.PUNISH_STATE
            return
        if not self.inbox:
            return

        message = self.inbox.popleft()
        mtype: AsyncMessageType = message["payload"]["message_type"]

        match mtype:
            case AsyncMessageType.COLLECT:
                self.__on_collect(message)
            case AsyncMessageType.SETUP:
                self.__on_setup(message)
            case AsyncMessageType.COMMIT:
                self.__on_commit(message)
            case AsyncMessageType.REVEAL:
                self.__on_reveal(message)
            case AsyncMessageType.CHOOSE:
                self.__on_choose(message)

    def __on_collect(self, message: dict) -> None:
        payload = message["payload"]
        originator_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])

        if originator_id > self.highest and self.phase <= 1:
            self.highest = originator_id
            id_set.add(self.unique_id)
            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.COLLECT,
                    "sender_id": originator_id,
                    "content": {"id_set": id_set},
                }
            )

        elif originator_id == self.unique_id and len(id_set) == self.model.num_agents:
            self.phase = 2
            self.id_set = id_set.copy()
            print(f"[Agent {self.unique_id}] starts SETUP phase.")
            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.SETUP,
                    "sender_id": originator_id,
                    "content": {"id_set": id_set},
                }
            )

    def __on_setup(self, message: dict) -> None:
        payload = message["payload"]
        originator_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])

        if originator_id != self.highest:
            return

        if not self.id_set:
            self.id_set = id_set.copy()
            self.phase = 2
            self.N_rand = random.randint(0, self.model.num_agents - 1)
            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.COMMIT,
                    "sender_id": self.unique_id,
                    "content": {"N_rand": self.N_rand},
                }
            )

        if self.unique_id != originator_id:
            self.send_to_successor(message["payload"])
        else:
            self.phase = 3
            print(f"[Agent {self.unique_id}] starts REVEAL phase.")
            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.REVEAL,
                    "sender_id": originator_id,
                    "content": {
                        "id_set": self.id_set,
                        "pairs": [],
                        "last_author": None,
                    },
                }
            )

    def __on_commit(self, message: dict) -> None:
        payload = message["payload"]
        predecessor_id = payload["sender_id"]
        N_predecessor = payload["content"]["N_rand"]

        if self.predecessor and predecessor_id != self.predecessor.unique_id:
            return

        self.commit_from_predecessor = N_predecessor
        self.send_to_successor(message["payload"])

    def __on_reveal(self, message: dict) -> None:
        payload = message["payload"]
        originator_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])
        pairs: list[tuple[int, int]] = list(payload["content"]["pairs"])
        last_author = payload["content"]["last_author"]

        if not self.id_set or id_set != self.id_set:
            return

        if last_author is not None and self.predecessor:
            if last_author == self.predecessor.unique_id:
                if not pairs or self.commit_from_predecessor is None:
                    return
                if pairs[-1][1] != self.commit_from_predecessor:
                    self.abort_protocol(self.commit_from_predecessor, pairs[-1][1])
                    return

        if all(pid != self.unique_id for pid, _ in pairs):
            pairs.append((self.unique_id, self.N_rand))

        self.send_to_successor(
            {
                "message_type": AsyncMessageType.REVEAL,
                "sender_id": originator_id,
                "content": {
                    "id_set": id_set,
                    "pairs": pairs,
                    "last_author": self.unique_id,
                },
            }
        )

        if self.unique_id == originator_id and len(pairs) == self.model.num_agents:
            total = sum(v for _, v in pairs)
            N = total % self.model.num_agents
            leader_id = int(sorted(id_set, reverse=True)[N])
            self.leader = leader_id
            print(
                f"[Agent {self.unique_id}] elected leader {leader_id}. Broadcasting result."
            )
            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.CHOOSE,
                    "sender_id": originator_id,
                    "content": {"id_set": id_set, "pairs": pairs, "leader": leader_id},
                }
            )

    def __on_choose(self, message: dict) -> None:
        payload = message["payload"]
        leader_id = payload["content"]["leader"]
        sender_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])

        if self.id_set != id_set:
            return

        self.leader = leader_id
        self.phase = 5
        self.send_to_successor(message["payload"])

        if self == self.model.starter and sender_id != self.unique_id:
            self.model.register_leader_report(sender_id)

        elif self.model.starter and sender_id != self.model.starter.unique_id:
            self.model.starter.inbox.append(
                {
                    "payload": {
                        "message_type": AsyncMessageType.CHOOSE,
                        "sender_id": self.unique_id,
                        "content": {"leader": leader_id, "id_set": list(self.id_set)},
                    }
                }
            )
