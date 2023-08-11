#!/usr/bin/python3
#
# Client part of eth-test-raw
# Copyright (c) Ci4Rail GmbH
#
import argparse
import socket
import struct
import sys
import time
import datetime
import signal
from ethtestraw_lib import (
    make_eth_header,
    get_eth_header,
    ETR_ETHER_TYPE,
    get_mac_address,
)  # noqa: E402

VERSION = "1.0.1"

tool_description = f"""
Version: {VERSION}.
Simple test tool for ethernet interfaces.
Tests a ethernet NIC against a NIC on a peer machine.
Requires the corresponding server running on the peer machine.
"""

PAYLOAD_BYTES = 1500
MAX_PACKET_SIZE = 2048  # for receive, should be a power of 2

seq_number = 0


class Stats:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.packets_sent = 0
        self.good_packets_received = 0
        self.error_count = 0
        self.retries = 0

    def elapsed_seconds(self):
        elapsed = datetime.datetime.now() - self.start_time
        return elapsed.total_seconds()

    def bytes_per_second(self):
        return (
            self.good_packets_received * (PAYLOAD_BYTES + 14)
        ) / self.elapsed_seconds()

    def __str__(self):
        return (
            f"sent pkts: {self.packets_sent:5d}, "
            f"errors/lost pkts: {self.error_count:3d}, "
            f"retry pkts: {self.retries:3d}, "
            f"{self.bytes_per_second()/1e6:6.2f} MByte/s"
        )


def update_stats(
    global_stats, interval_stats, packets_sent, packets_received, error_count, retry_count
):
    for stats in [global_stats, interval_stats]:
        stats.packets_sent += packets_sent
        stats.good_packets_received += packets_received
        stats.error_count += error_count
        stats.retries += retry_count


def client(args):
    global seq_number

    exit_code = 0
    src_mac_string = get_mac_address(args.ifname)
    src_mac = mac_address_string_to_bytes(src_mac_string)

    print(f"Own Mac: Interface={args.ifname}, " f"{src_mac_string} dest:{args.dst_mac}")
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETR_ETHER_TYPE))
    s.bind((args.ifname, 0))
    s.settimeout(args.timeout)

    global_stats = Stats()
    interval_stats = Stats()

    signal.signal(signal.SIGINT, signal.default_int_handler)

    send_seq = 0

    try:
        while exit_code == 0:
            if (
                args.runtime is not None
                and global_stats.elapsed_seconds() > args.runtime  # noqa: W503
            ):
                break

            try:
                while True:
                    send_frame(src_mac, s, send_seq, args)
                    if recv_frame(src_mac, s, args) == "ok":
                        break
                    # Retry if frame is not valid, but error shall be ignored
                    update_stats(global_stats, interval_stats, 1, 0, 0, 1)
                    if global_stats.retries >= args.max_retries:
                        print(f"Stopped because max retries {args.max_retries} reached")
                        exit_code = 1
                        break
                    if args.delay is not None:
                        time.sleep(args.delay / 1e6)

                update_stats(global_stats, interval_stats, 1, 1, 0, 0)

            except (socket.timeout, RuntimeError) as err:
                if args.verbose:
                    print(f"seq {send_seq}: Rx error: {err}")
                update_stats(global_stats, interval_stats, 1, 0, 1, 0)

                if (
                    args.error_threshold != -1
                    and global_stats.error_count >= args.error_threshold  # noqa: W503
                ):
                    print(f"Stopped because error threshold {args.error_threshold} reached")
                    exit_code = 1
                    break
            send_seq += 1

            if interval_stats.elapsed_seconds() > args.interval:
                print(interval_stats)
                interval_stats = Stats()

            if args.delay is not None:
                time.sleep(args.delay / 1e6)

    except KeyboardInterrupt:
        print("Stopped")
    finally:
        print(f"Total Stats: {global_stats}")

    sys.exit(exit_code)


def send_frame(src_mac, s, seq_number, args):
    eth_hdr = make_eth_header(src_mac, mac_address_string_to_bytes(args.dst_mac))
    payload = make_payload(PAYLOAD_BYTES, seq_number)
    frame = eth_hdr + payload
    s.send(frame)


# return "retry" if the frame is not valid, but error shall be ignored
# return "ok" if the frame is valid
# raise RuntimeError if the frame is not valid and error shall be reported
def recv_frame(src_mac, s, args):
    pkt_bytes = s.recv(MAX_PACKET_SIZE)
    return validate_frame(pkt_bytes, src_mac, args)


err_inject_count = 0
# return "retry" if the frame is not valid, but error shall be ignored
# return "ok" if the frame is valid
# raise RuntimeError if the frame is not valid and error shall be reported
def validate_frame(pkt_bytes, src_mac, args):
    global seq_number
    global err_inject_count
    rcv_dst_mac, rcv_src_mac, rcv_type = get_eth_header(pkt_bytes)

    rcv_dst_mac_str = mac_address_bytes_to_string(rcv_dst_mac)
    rcv_src_mac_str = mac_address_bytes_to_string(rcv_src_mac)

    if rcv_dst_mac != src_mac:
        print(f"WARN: Bad dst mac {rcv_dst_mac_str} received. Expected {mac_address_bytes_to_string(src_mac)}. Ignoring")
        return "retry"
        

    if rcv_src_mac_str != args.dst_mac.lower():
        raise RuntimeError(
            f"Bad src mac {rcv_src_mac_str} received. Expected {args.dst_mac}"
        )

    if rcv_type != ETR_ETHER_TYPE:
        raise RuntimeError(
            f"Bad eth type {rcv_type} received. Expected {ETR_ETHER_TYPE}"
        )

    rcv_seq_number = get_payload(pkt_bytes)[0]

    # # Error Injection
    # err_inject_count += 1
    # if err_inject_count % 8 == 0:
    #     return True

    exp_seq_number = seq_number

    seq_number = rcv_seq_number + 1  # resync with sender

    if rcv_seq_number != exp_seq_number:
        raise RuntimeError(
            f"Bad seq number {rcv_seq_number} received. Expected {exp_seq_number}"
        )
    return "ok"

def make_payload(payload_length, seq_number):
    payload_hdr = struct.pack("!L", seq_number)
    payload = payload_hdr + bytes(payload_length - len(payload_hdr))
    return payload


def get_payload(pkt_bytes):
    return struct.unpack("!L", pkt_bytes[14:18])


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
        "-d",
        "--delay",
        help="Delay in microseconds between pings (default: None)",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-t",
        "--timeout",
        help="Timeout in seconds to wait for peer reply (default: 0.1)",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "-e",
        "--error_threshold",
        help="stop after n errors, -1 to stop never (default: 1)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--max-retries",
        help="stop after n retries (default: 50)",
        type=int,
        default=50,
    )
    parser.add_argument(
        "-i",
        "--interval",
        help="print statistics after x seconds (default: 0.5)",
        type=float,
        default=0.5,
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
