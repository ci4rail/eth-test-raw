#
# Client part of eth-test-raw
# Copyright (c) Ci4Rail GmbH
#
import argparse
import socket
import fcntl
import struct
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common import make_eth_header  # noqa: E402

tool_description = """
Simple test tool for ethernet interfaces.
Tests a ethernet NIC against a NIC on a peer machine.
Requires the corresponding server running on the peer machine
"""

PAYLOAD_BYTES = 1500


def client(args):
    src_mac_string = get_mac_address(args.ifname)
    src_mac = mac_address_string_to_bytes(src_mac_string)

    print(
        f"Own Mac: Interface={args.ifname}, "
        "{src_mac_string} dest:{mac_address_bytes_to_string(dest_mac)}"
    )
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((args.ifname, 0))

    for seq_number in range(2):
        eth_hdr = make_eth_header(src_mac, args.dst_mac)
        payload = make_payload(PAYLOAD_BYTES, seq_number)
        frame = eth_hdr + payload

        print(frame)

        s.send(frame)


def make_payload(payload_length, seq_number):
    payload_hdr = struct.pack("!L", seq_number)
    payload = payload_hdr + bytes(payload_length - len(payload_hdr))
    return payload


def get_mac_address(interface_name):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(
        s.fileno(), 0x8927, struct.pack("256s", bytes(interface_name, "utf-8")[:15])
    )
    return ":".join("%02x" % b for b in info[18:24])


def mac_address_string_to_bytes(addr_string):
    mac_elems = addr_string.split(":")
    if len(mac_elems) != 6:
        raise ValueError(f"malformed mac: ${addr_string}")

    data = bytearray(6)
    for i in range(6):
        data[i] = int(mac_elems[i], 16)
    return data


def mac_address_bytes_to_string(addr_bytes):
    s = ""
    for i in range(6):
        s += "%02x" % addr_bytes[i]
        if i < 5:
            s += ":"
    return s


def command_line_args_parsing():
    parser = argparse.ArgumentParser(description=tool_description)
    parser.add_argument("ifname", help="Name of local interface (e.g. eth0)")
    parser.add_argument("dst_mac", help="Peer's MAC address (e.g. 00:11:22:33:44:55)")
    parser.add_argument(
        "-r",
        "--runtime",
        help="runtime in seconds. (default: run forever)",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-b",
        "--burst-length",
        help="Number of frames to send as burst until to wait for reply (default: 1)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "-d",
        "--delay",
        help="Delay in microseconds between subsequent bursts (default: None)",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose",
        action="store_true",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = command_line_args_parsing()
    client(args)
