# GateGuard: New file. Importers: agent_comm/coordinator.py, agent_comm/__init__.py, tests/test_agent_comm.py. Affected API: none. Data schemas: AgentChannel, AgentMessage. User instruction: Phase 4 V2.0 — agent_comm channel manager per enhancement doc.

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import AgentChannel, AgentMessage, MessageType

logger = logging.getLogger(__name__)


class AgentChannelManager:
    def __init__(self, state_dir: str | Path = ".agent_comm_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._channels_path = self.state_dir / "channels.jsonl"
        self._messages_path = self.state_dir / "messages.jsonl"
        self._channels: dict[str, AgentChannel] = {}
        self._message_queue: dict[str, list[AgentMessage]] = {}
        self._load()

    def create_channel(self, name: str, participants: list[str]) -> AgentChannel:
        if name in self._channels:
            logger.warning("channel already exists: %s", name)
            return self._channels[name]
        channel = AgentChannel(name=name, participants=participants)
        self._channels[name] = channel
        self._message_queue[name] = []
        self._append_channel(channel)
        logger.info("created channel: %s with %d participants", name, len(participants))
        return channel

    def get_channel(self, name: str) -> AgentChannel | None:
        return self._channels.get(name)

    def list_channels(self) -> list[AgentChannel]:
        return list(self._channels.values())

    def close_channel(self, name: str) -> bool:
        if name not in self._channels:
            logger.warning("channel not found: %s", name)
            return False
        self._channels[name].is_active = False
        logger.info("closed channel: %s", name)
        return True

    def send_message(self, message: AgentMessage) -> bool:
        channel = self._channels.get(message.channel_name)
        if not channel or not channel.is_active:
            logger.warning("cannot send to inactive or unknown channel: %s", message.channel_name)
            return False
        if message.sender_id not in channel.participants:
            logger.warning("sender %s not in channel %s", message.sender_id, message.channel_name)
            return False
        queue = self._message_queue.setdefault(message.channel_name, [])
        queue.append(message)
        self._append_message(message)
        logger.debug(
            "message %s from %s to %s on %s",
            message.message_id,
            message.sender_id,
            message.recipient_id,
            message.channel_name,
        )
        return True

    def receive_messages(self, agent_id: str, channel_name: str, since: str | None = None) -> list[AgentMessage]:
        queue = self._message_queue.get(channel_name, [])
        messages = [m for m in queue if m.recipient_id == agent_id or m.recipient_id == "*"]
        if since:
            messages = [m for m in messages if m.timestamp > since]
        logger.debug("agent %s received %d messages on %s", agent_id, len(messages), channel_name)
        return messages

    def broadcast(self, sender_id: str, channel_name: str, message_type: MessageType, payload: dict) -> int:
        channel = self._channels.get(channel_name)
        if not channel or not channel.is_active:
            logger.warning("cannot broadcast to inactive or unknown channel: %s", channel_name)
            return 0
        sent = 0
        for participant in channel.participants:
            if participant == sender_id:
                continue
            msg = AgentMessage(
                sender_id=sender_id,
                recipient_id=participant,
                channel_name=channel_name,
                message_type=message_type,
                payload=payload,
            )
            queue = self._message_queue.setdefault(channel_name, [])
            queue.append(msg)
            self._append_message(msg)
            sent += 1
        logger.info("broadcast from %s to %d agents on %s", sender_id, sent, channel_name)
        return sent

    def _append_channel(self, channel: AgentChannel):
        with open(self._channels_path, "a") as f:
            f.write(json.dumps(channel.to_dict()) + "\n")

    def _append_message(self, message: AgentMessage):
        with open(self._messages_path, "a") as f:
            f.write(json.dumps(message.to_dict()) + "\n")

    def _load(self):
        if self._channels_path.exists():
            with open(self._channels_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ch = AgentChannel.from_dict(json.loads(line))
                        self._channels[ch.name] = ch
                        if ch.name not in self._message_queue:
                            self._message_queue[ch.name] = []
                    except Exception as e:
                        logger.warning("failed to load channel: %s", e)
        if self._messages_path.exists():
            with open(self._messages_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = AgentMessage.from_dict(json.loads(line))
                        self._message_queue.setdefault(msg.channel_name, []).append(msg)
                    except Exception as e:
                        logger.warning("failed to load message: %s", e)
