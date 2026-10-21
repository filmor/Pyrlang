# Copyright 2018, Erlang Solutions Ltd, and S2HC Sweden AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The module implements incoming TCP dist_proto protocol (i.e. initiated
by another node with the help of EPMD). Protocol only performs handling of
incoming data, the socket is handled by the Async Engine (pyrlang.async).
"""

import logging
import random
import struct

from term import util

from pyrlang.dist_proto.base_dist_protocol import BaseDistProtocol, DistributionError

LOG = logging.getLogger(__name__)


# LOG.setLevel(logging.INFO)


class DistServerProtocol(BaseDistProtocol):
    """Protocol handles incoming connections from other nodes."""

    def __init__(self, node_name: str) -> None:
        super().__init__(node_name=node_name)

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        self.state_ = self.DISCONNECTED

    def on_packet(self, data: bytes) -> bytes:
        """Handle incoming dist_proto packet

        :param data: The packet after the header had been removed
        """
        if self.state_ == self.CONNECTED:  # this goes first for perf reasons
            return self.on_packet_connected(data)

        elif self.state_ == self.RECV_NAME:
            return self.on_packet_recvname(data)

        elif self.state_ == self.WAIT_CHALLENGE_REPLY:
            return self.on_packet_challengereply(data)

        raise DistributionError(f"Unknown state for on_packet: {self.state_}")

    def on_packet_recvname(self, data: bytes) -> bytes:
        """Handle RECV_NAME command, the first packet in a new connection."""
        if not data.startswith(b"N"):
            self.destroy()
            self.raise_protocol_error("Handshake 'N' packet expected (OTP 26+)")

        self.dist_vsn_ = 6
        self._set_peer_flags(struct.unpack(">Q", data[1:9])[0])
        creation = util.u32(data[9:13])
        nlen = util.u16(data[13:15])
        self.peer_name_ = data[15 : 15 + nlen].decode("utf-8")
        LOG.info(
            "RECV_NAME: (version %d) %s (creation %d)",
            self.dist_vsn_,
            self.peer_name_,
            creation,
        )

        # Report
        self._send_packet2(b"sok")

        self.my_challenge_ = int(random.random() * 0x7FFFFFFF)
        self._send_challenge(self.my_challenge_)

        self.state_ = self.WAIT_CHALLENGE_REPLY

        return b""  # assume everything is consumed

    def on_packet_challengereply(self, data: bytes) -> bytes:
        if not data.startswith(b"r"):
            return self.raise_protocol_error(
                f"Unexpected packet (expecting CHALLENGE_REPLY) {data!r}"
            )

        peers_challenge = util.u32(data, 1)
        peer_digest = data[5:]
        LOG.info("challengereply: peer's challenge %s", peers_challenge)

        if self.my_challenge_ is None:
            return self.raise_protocol_error(
                "In on_packet_challengereply: self.my_challenge_ is None [internal error]"
            )

        my_cookie = self.get_node().node_opts_.cookie_
        if not self.check_digest(
            digest=peer_digest, challenge=self.my_challenge_, cookie=my_cookie
        ):
            self.raise_protocol_error("Disallowed node connection (check the cookie)")
            # raise

        self._send_challenge_ack(peers_challenge, my_cookie)
        self.packet_len_size_ = 4
        self.state_ = self.CONNECTED
        self.report_dist_connected()

        # TODO: start timer with node_opts_.network_tick_time_

        LOG.info("Incoming dist established from %s", self.peer_name_)
        return b""  # assume data is consumed

    def _send_challenge(self, my_challenge: int) -> None:
        n = self.get_node()
        LOG.info(
            "Sending challenge (our number is %d) %s", my_challenge, self.node_name_
        )
        name = self.node_name_.encode("utf-8")
        msg = (
            b"N"
            + struct.pack(
                ">QIIH",
                n.node_opts_.dflags_,
                my_challenge,
                n.dist_.creation_,
                len(name),
            )
            + name
        )
        self._send_packet2(msg)

    def _send_challenge_ack(self, peers_challenge: int, cookie: str) -> None:
        """After cookie has been verified, send the confirmation by digesting
        our cookie with the remote challenge
        """
        digest = DistServerProtocol.make_digest(peers_challenge, cookie)
        self._send_packet2(b"a" + digest)


__all__ = ["DistServerProtocol"]
