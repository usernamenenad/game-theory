from collections import deque
import random
import mesa
from src.uni_async.types import AsyncMessageType
from typing import Optional


class UniAsyncAgent(mesa.Agent):
    """Asynchronous leader election consensus in a unidirectional ring."""

    PUNISH_STATE = None

    def __init__(self, model: mesa.Model) -> None:
        """Initialize agent state, communication buffers, and local protocol variables.

        Each agent has a reference to the model, predecessor and successor links,
        a message inbox, random number commitments, and metadata for detecting cheating.
        """
        super().__init__(model)
        self.leader: Optional[int] = None
        self.highest = -1
        self.phase = 0
        self.id_set: set[int] = set()
        self.N_rand_commit: Optional[int] = None
        self.N_rand_reveal: Optional[int] = None
        self.commit_from_predecessor: Optional[int] = None
        self.commit_records: dict[int, int] = {}
        self.inbox: deque[dict] = deque()
        self.predecessor: "UniAsyncAgent" | None = None
        self.successor: "UniAsyncAgent" | None = None
        self.is_malicious: bool = False

    def send_to_successor(self, payload: dict) -> None:
        """Send a message asynchronously to the next agent in the ring.

        Messages are handled by the model’s network, which introduces delivery delay.
        This function is used by all protocol phases to propagate messages forward.
        """
        if self.successor:
            self.model.network.send(self.unique_id, self.successor.unique_id, payload)

    def abort_protocol(self, expected: int, revealed: int) -> None:
        """Abort the election if cheating by the predecessor is detected.

        Triggered when a predecessor reveals a value different from its earlier commit.
        The agent signals this to the model by setting the abort flag.
        """
        print(
            f"[Agent {self.unique_id}] detected cheating by predecessor! "
            f"Committed {expected}, revealed {revealed}"
        )
        self.model.abort_flag = True
        self.leader = UniAsyncAgent.PUNISH_STATE

    def start_protocol(self) -> None:
        """Start the leader election by initiating the COLLECT phase.

        The initiating agent sends a message containing its ID around the ring.
        Each agent appends its ID; when the initiator receives all IDs, it proceeds
        to the SETUP phase.
        """
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
                "content": {"id_set": list(self.id_set)},
            }
        )

    def step(self) -> None:
        """Process one pending message per tick.

        The agent dequeues a message, identifies its type, and delegates handling
        to the appropriate phase-specific method. If the protocol was aborted,
        no further actions are taken.
        """
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
        """Handle COLLECT messages used to gather all agent IDs.

        Each agent appends its ID and forwards the message. When the originator
        receives the message containing all unique IDs, it transitions to SETUP.
        """
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
                    "content": {"id_set": list(id_set)},
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
                    "content": {"id_set": list(id_set)},
                }
            )

    def __on_setup(self, message: dict) -> None:
        """Handle SETUP messages and create random commitments.

        Each agent selects a random number (commit) and, if malicious, decides a
        different reveal value. The commit is sent to the successor, and when the
        originator gets its SETUP message back, it starts the REVEAL phase.
        """
        payload = message["payload"]
        originator_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])

        if originator_id != self.highest:
            return

        if not self.id_set:
            self.id_set = id_set.copy()

        if self.phase < 2 or (self.is_malicious and self.unique_id == originator_id):
            self.phase = 2
            self.N_rand_commit = random.randint(0, self.model.num_agents - 1)
            if self.is_malicious:
                diff = random.randint(1, self.model.num_agents - 1)
                self.N_rand_reveal = (self.N_rand_commit + diff) % self.model.num_agents
                print(
                    f"[Agent {self.unique_id}] MALICIOUS: committing {self.N_rand_commit} "
                    f"but will reveal {self.N_rand_reveal}."
                )
            else:
                self.N_rand_reveal = self.N_rand_commit

            self.send_to_successor(
                {
                    "message_type": AsyncMessageType.COMMIT,
                    "sender_id": self.unique_id,
                    "content": {"N_rand": self.N_rand_commit},
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
                        "id_set": list(self.id_set),
                        "pairs": [],
                        "last_author": None,
                    },
                }
            )

    def __on_commit(self, message: dict) -> None:
        """Handle COMMIT messages and store predecessor's committed number.

        Each agent records its predecessor’s commit in both local and global
        dictionaries. This value is later compared with the revealed one for
        integrity verification during the REVEAL phase.
        """
        payload = message["payload"]
        predecessor_id = payload["sender_id"]
        N_predecessor = payload["content"]["N_rand"]
        if self.predecessor and predecessor_id != self.predecessor.unique_id:
            return
        self.commit_from_predecessor = N_predecessor
        self.commit_records[predecessor_id] = N_predecessor
        self.send_to_successor(message["payload"])

    def __on_reveal(self, message: dict) -> None:
        """Handle REVEAL messages and verify all commitments.

        Agents check that revealed numbers match previously received commits.
        If a mismatch is detected, the protocol is aborted and cheating is logged.
        Once all reveals are collected, the originator computes and announces the leader.
        """
        payload = message["payload"]
        originator_id = payload["sender_id"]
        id_set = set(payload["content"]["id_set"])
        pairs: list[tuple[int, int]] = list(payload["content"]["pairs"])
        last_author = payload["content"]["last_author"]
        if not self.id_set or id_set != self.id_set:
            return
        for pid, revealed_val in pairs:
            if pid in self.commit_records:
                if revealed_val != self.commit_records[pid]:
                    self.abort_protocol(self.commit_records[pid], revealed_val)
                    return
        if last_author is not None and self.predecessor:
            if last_author == self.predecessor.unique_id:
                if not pairs or self.commit_from_predecessor is None:
                    return
                if pairs[-1][1] != self.commit_from_predecessor:
                    self.abort_protocol(self.commit_from_predecessor, pairs[-1][1])
                    return
        if all(pid != self.unique_id for pid, _ in pairs):
            if self.N_rand_reveal is None:
                if self.N_rand_commit is None:
                    self.N_rand_commit = random.randint(0, self.model.num_agents - 1)
                self.N_rand_reveal = self.N_rand_commit
            pairs.append((self.unique_id, int(self.N_rand_reveal)))
        self.send_to_successor(
            {
                "message_type": AsyncMessageType.REVEAL,
                "sender_id": originator_id,
                "content": {
                    "id_set": list(id_set),
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
                    "content": {
                        "id_set": list(id_set),
                        "pairs": pairs,
                        "leader": leader_id,
                    },
                }
            )

    def __on_choose(self, message: dict) -> None:
        """Handle CHOOSE messages to finalize and distribute the leader decision.

        The elected leader ID is propagated around the ring so all agents agree
        on the result. Each agent records the leader and reports completion to
        the model once it receives confirmation.
        """
        payload = message["payload"]
        leader_id = payload["content"]["leader"]
        id_set = set(payload["content"]["id_set"])
        if self.id_set != id_set:
            return
        self.leader = leader_id
        self.phase = 5
        self.send_to_successor(message["payload"])
        if self == self.model.starter:
            self.model.register_leader_report(self.unique_id)
        if self.model.starter and self != self.model.starter:
            self.model.starter.inbox.append(
                {
                    "payload": {
                        "message_type": AsyncMessageType.CHOOSE,
                        "sender_id": self.unique_id,
                        "content": {"leader": leader_id, "id_set": list(self.id_set)},
                    }
                }
            )
