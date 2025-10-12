from collections import deque
from typing import Any, Self

import mesa
import random

from src.uni_async.types import AsyncMessageType


class UniAsyncAgent(mesa.Agent):
    def __init__(self, model: mesa.Model) -> None:
        super().__init__(model)

        self.leader: int | None = None

        self.highest = -1
        self.phase = 0
        self.id_set: set[int] = set()
        self.N_rand: int = -1
        self.commit_from_predecessor = -1

        self.inbox: deque[dict[str, Any]] = deque()
        self.predecessor: Self | None = None
        self.successor: Self | None = None

    def start_protocol(self) -> None:
        """
        Corresponds to `UponWaking` method.
        """

        if self.phase != 0:
            return

        print(f"[Agent {self.unique_id}]: Waking up and starting protocol.")

        self.highest = self.unique_id
        self.phase = 1
        self.id_set.add(self.unique_id)

        if self.successor:
            self.send_to_successor(
                self.successor.unique_id,
                payload={
                    "message_type": AsyncMessageType.COLLECT,
                    "sender_id": self.unique_id,
                    "content": {
                        "id_set": self.id_set,
                    },
                },
            )

    def send_to_successor(self, dest: int, payload: dict[str, Any]) -> None:
        """Sends a message to agent's successor in the ring."""

        self.model.network.send(self.unique_id, dest, payload)  # type: ignore

    def step(self) -> None:
        if self.leader is not None:
            return

        if not self.inbox:
            return

        message = self.inbox.popleft()
        message_type: AsyncMessageType = message["payload"]["type"]

        match message_type:
            case AsyncMessageType.COLLECT:
                self.__on_collect(message)
            case AsyncMessageType.SETUP:
                self.__on_setup(message)
            case AsyncMessageType.COMMIT:
                self.__on_commit(message)
            case AsyncMessageType.REVEAL:
                self.__on_reveal(message)

    def __on_collect(self, message: dict[str, Any]) -> None:
        payload: dict[str, Any] = message["payload"]
        originator_id: int = payload["sender_id"]
        id_set: set[int] = payload["content"]["id_set"]

        """
        Ignore collect if not from originator.
        """
        if self.highest < originator_id:
            return

        """
        Agent got a collect message. Verify
        that there are N agents.
        """
        if self.unique_id not in id_set:
            if self.model.num_agents >= len(id_set):  # type: ignore
                return
            id_set.add(self.unique_id)

        if self.unique_id == originator_id and len(id_set) == self.model.num_agents:  # type: ignore
            self.id_set = id_set.copy()
            self.phase = 2

            if self.successor:
                self.send_to_successor(
                    self.successor.unique_id,
                    payload={
                        "type": AsyncMessageType.SETUP,
                        "sender_id": originator_id,
                        "content": {
                            "id_set": id_set,
                        },
                    },
                )

        if self.successor:
            self.send_to_successor(
                self.successor.unique_id,
                payload={
                    "type": AsyncMessageType.COLLECT,
                    "sender_id": originator_id,
                    "content": {
                        "id_set": id_set,
                    },
                },
            )

    def __on_setup(self, message: dict[str, Any]) -> None:
        payload: dict[str, Any] = message["payload"]
        originator_id: int = payload["sender_id"]
        id_set: set[int] = payload["content"]["id_set"]

        if self.highest != originator_id:
            return

        if not self.id_set:
            if len(id_set) == self.model.num_agents:  # type: ignore
                return

            self.id_set.update(id_set)
            self.phase = 2
            self.N_rand = random.randint(0, self.model.num_agents - 1)  # type: ignore

            if self.successor:
                self.send_to_successor(
                    self.successor.unique_id,
                    payload={
                        "type": AsyncMessageType.COMMIT,
                        "sender_id": self.unique_id,
                        "content": {
                            "N_rand": self.N_rand,
                        },
                    },
                )

        if self.unique_id == originator_id:
            self.phase = 3

            if self.successor:
                self.send_to_successor(
                    self.successor.unique_id,
                    payload={
                        "type": AsyncMessageType.REVEAL,
                        "sender_id": self.unique_id,
                        "content": {
                            "id_set": self.id_set,
                            "pairs": [],
                            "last_author": None,
                        },
                    },
                )
        else:
            if self.successor:
                self.send_to_successor(
                    self.successor.unique_id,
                    payload={
                        "type": AsyncMessageType.SETUP,
                        "sender_id": originator_id,
                        "content": {
                            "id_set": id_set,
                        },
                    },
                )

    def __on_commit(self, message: dict[str, Any]) -> None:
        payload: dict[str, Any] = message["payload"]
        predecessor_id: int = payload["sender_id"]
        N_rand_predecessor: int = payload["content"]["N_rand"]

        if self.predecessor and predecessor_id != self.predecessor.unique_id:
            return

        self.commit_from_predecessor = N_rand_predecessor

    def __on_reveal(self, message: dict[str, Any]) -> None:
        payload: dict[str, Any] = message["payload"]
        originator_id: int = payload["sender_id"]
        id_set: set[int] = payload["content"]["id_set"]
        pairs: list[tuple[int, int]] = payload["content"]["pairs"]
        last_author: int | None = payload["content"]["last_author"]

        if not self.id_set or id_set != self.id_set:
            return

        if last_author is not None:
            if self.predecessor and self.predecessor.unique_id != last_author:
                return

            if not pairs:
                return

            last_pair = pairs[-1]

            if self.predecessor and last_pair[0] != self.predecessor.unique_id:
                return

            if self.commit_from_predecessor == -1:
                return

            if last_pair[1] != self.commit_from_predecessor:
                return
