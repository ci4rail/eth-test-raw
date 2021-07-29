import struct

ETR_ETHER_TYPE = 0xccdd     # Type value in ethernet frame


def make_eth_header(src_mac, dest_mac):
    eth_hdr = struct.pack("!6s6sH", dest_mac, src_mac, ETR_ETHER_TYPE)
    return eth_hdr


def get_eth_header(pkt_bytes):
    return struct.unpack("!6s6sH", pkt_bytes[0:14])
