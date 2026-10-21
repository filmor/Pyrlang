import asyncio
import struct
from unittest.mock import AsyncMock, Mock

import pytest
from term import Pid

from pyrlang.dist_proto import version
from pyrlang.dist_proto.base_dist_protocol import BaseDistProtocol
from pyrlang.dist_proto.client import DistClientProtocol
from pyrlang.dist_proto.epmd_client import EPMDClient
from pyrlang.dist_proto.flags import (
    DEFAULT_DFLAGS,
    DFLAG_MANDATORY_25_DIGEST,
    DFLAG_UNLINK_ID,
    DFLAG_V4_NC,
    MANDATORY_DFLAGS,
    MANDATORY_DFLAGS_25,
)
from pyrlang.dist_proto.server import DistServerProtocol
from pyrlang.errors import DistributionError, EPMDClientError
from pyrlang.node import Node
from pyrlang.process import Process


def test_version_five_is_not_negotiated() -> None:
    assert not version.dist_version_check((5, 5))
    assert version.dist_version_check((6, 5))
    with pytest.raises(DistributionError, match="Unsupported distribution version"):
        DistClientProtocol("local@host", 5)


@pytest.mark.parametrize("incoming", [True, False])
@pytest.mark.parametrize("missing", [DFLAG_UNLINK_ID, DFLAG_V4_NC, MANDATORY_DFLAGS_25])
def test_handshake_rejects_missing_capabilities(
    incoming: bool, missing: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = (
        DistServerProtocol("local@host")
        if incoming
        else DistClientProtocol("local@host", 6)
    )
    transport = Mock()
    protocol.transport_ = transport
    send = Mock()
    monkeypatch.setattr(protocol, "_send_packet2", send)
    flags = MANDATORY_DFLAGS & ~missing
    name = b"remote@host"
    if incoming:
        packet = b"N" + struct.pack(">QIH", flags, 1, len(name)) + name
        receive = protocol.on_packet_recvname
    else:
        packet = b"N" + struct.pack(">QIIH", flags, 123, 1, len(name)) + name
        receive = protocol.on_packet_recvchallenge
    with pytest.raises(DistributionError, match="mandatory OTP 26 capabilities"):
        receive(packet)
    transport.close.assert_called_once()
    send.assert_not_called()


@pytest.mark.parametrize("incoming", [True, False])
def test_handshake_rejects_old_packets(incoming: bool) -> None:
    if incoming:
        protocol = DistServerProtocol("local@host")
        receive = protocol.on_packet_recvname
    else:
        protocol = DistClientProtocol("local@host", 6)
        receive = protocol.on_packet_recvchallenge
    with pytest.raises(DistributionError, match="Handshake 'N' packet expected"):
        receive(b"n" + struct.pack(">HI", 5, 0) + b"remote@host")


@pytest.mark.parametrize("use_digest", [False, True])
def test_version_six_handshake(
    use_digest: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    flags = DEFAULT_DFLAGS
    if use_digest:
        flags = DFLAG_MANDATORY_25_DIGEST | DFLAG_UNLINK_ID | DFLAG_V4_NC
    node = Mock()
    node.node_opts_.dflags_ = flags
    node.node_opts_.cookie_ = "cookie"
    node.get_cookie.return_value = "cookie"
    node.dist_.creation_ = 0x12345678
    monkeypatch.setattr(BaseDistProtocol, "get_node", lambda self: node)

    client = DistClientProtocol("cl\u00efent@host", 6)
    server = DistServerProtocol("s\u00ebrver@host")
    client_send = Mock()
    server_send = Mock()
    monkeypatch.setattr(client, "_send_packet2", client_send)
    monkeypatch.setattr(server, "_send_packet2", server_send)
    monkeypatch.setattr(client, "report_dist_connected", Mock())
    monkeypatch.setattr(server, "report_dist_connected", Mock())

    client._send_name()
    name = client_send.call_args.args[0]
    server.on_packet_recvname(name + b"ignored extension")
    client.on_packet_recvstatus(server_send.call_args_list[0].args[0])
    client.on_packet_recvchallenge(server_send.call_args.args[0] + b"ignored extension")
    server.on_packet_challengereply(client_send.call_args.args[0])
    client.on_packet_recvchallenge_ack(server_send.call_args.args[0])

    assert client.state_ == client.CONNECTED
    assert server.state_ == server.CONNECTED
    assert client.packet_len_size_ == server.packet_len_size_ == 4
    assert client.peer_name_ == server.node_name_
    assert server.peer_name_ == client.node_name_
    assert client.peer_flags_ & MANDATORY_DFLAGS == MANDATORY_DFLAGS
    assert server.peer_flags_ & MANDATORY_DFLAGS == MANDATORY_DFLAGS


@pytest.mark.parametrize("legacy", [False, True])
def test_epmd_requires_extended_creation(legacy: bool) -> None:
    async def read_reply() -> int:
        client = EPMDClient()
        client.reader_ = asyncio.StreamReader()
        if legacy:
            client.reader_.feed_data(b"\x79\x00\x00\x01")
        else:
            client.reader_.feed_data(b"\x76\x00\xfe\xdc\xba\x98")
        client.reader_.feed_eof()
        return await client._read_alive2_reply()

    if legacy:
        with pytest.raises(EPMDClientError, match="ALIVE2_X_RESP"):
            asyncio.run(read_reply())
    else:
        assert asyncio.run(read_reply()) == 0xFEDCBA98


def test_unlink_uses_nonzero_id_and_preserves_reestablished_link() -> None:
    node = object.__new__(Node)
    node.node_name_ = "local@host"
    node._prev_unlink_identifier = 0
    local = Pid(node.node_name_, 1, 0, 1)
    remote = Pid("remote@host", 2, 0, 1)
    process = object.__new__(Process)
    process._links = {remote: True}
    node.processes_ = {local: process}
    node.dist_nodes_ = {remote.node_name_: BaseDistProtocol(node.node_name_)}
    node._establish_connection = AsyncMock()
    node.dist_command = AsyncMock()

    asyncio.run(node.unlink(local, remote))
    node.dist_command.assert_awaited_once_with(
        remote.node_name_, ("unlink_id", 1, local, remote)
    )
    asyncio.run(node.unlink(local, remote))
    assert node.dist_command.await_count == 1
    asyncio.run(node._unlink_id_ack(1, remote, local))
    assert process._link_state(remote) is None

    process._set_link_state(remote, True)
    asyncio.run(node._unlink_id_ack(1, remote, local))
    assert process._link_state(remote) is True
