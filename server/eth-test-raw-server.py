#
# Server part of eth-test-raw
# Copyright (c) Ci4Rail GmbH
#
import socket
import struct
import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common import ETR_ETHER_TYPE, make_eth_header  # noqa: E402

MAX_PACKET_SIZE = 2048  # should be a power of 2


def server(args):
    # listen on frames with our specific ETR_ETHER_TYPE
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETR_ETHER_TYPE))
    s.bind((args.ifname, 0))

    print("Start listening")
    while True:
        pkt_bytes, address = s.recvfrom(MAX_PACKET_SIZE)
        recv_eth_header = get_eth_header(pkt_bytes)

        print(f"received{recv_eth_header} address {address}")
        payload = pkt_bytes[14:]

        # echo frame with reversed src/dest mac
        send_eth_header = make_eth_header(recv_eth_header[0], recv_eth_header[1])
        frame = send_eth_header + payload
        s.send(frame)

        if args.verbose:
            print(frame)


def get_eth_header(pkt_bytes):
    return struct.unpack("!6s6sH", pkt_bytes[0:14])


def command_line_args_parsing():
    parser = argparse.ArgumentParser(description="Server for eth-test-raw client")
    parser.add_argument("ifname", help="Name of local interface (e.g. eth0)")
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose",
        action="store_true",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = command_line_args_parsing()
    server(args)
    sys.exit(0)
