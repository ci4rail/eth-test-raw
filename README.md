# eth-test-raw
Simple test tool for ethernet interfaces.

Tests a ethernet NIC against a NIC on a peer machine using raw ethernet packets.
Requires the corresponding server running on the peer machine.

The purpose of this tool is to test the stability of the NIC hardware, for example to use it for environmental qualification tests. It is not optimized for throughput.

## Platform compatibility
Tested only under Linux (Rasperian OS and Yocto arm64). May work on Windows.

## How to Use

Connect device with the NIC to be tested to a peer machine via Ethernet.
You may have L2 switches in between, but no routers.

Deploy this repository, or at least the folders `client`, `server` and common to both machines.
Let's say, you have it deployed under ~/eth-raw-test.

### On the Server
You need to know the interface name of the peer machine's NIC, e.g. `eth0`.

Find out the MAC address of the peer machine's NIC:
```bash
ip link show eth0
```
Record the value for `link/ether`, e.g. `dc:a6:32:51:0e:e7`

Start server on peer machine with root priviledges. Specify the name of the peer machine's NIC:
```bash
python3 server/eth-test-raw-server.py eth0
```

### On the Client

Start the client specifying the interface name of the NIC to test and the peer machine's MAC address.
You must have root priviledges:
```bash
python3 /data/eth-test-raw/client/eth-test-raw-client.py enp5s0 dc:a6:32:51:0e:e7
```

In the above form, the client runs forever, until it is aborted, or the maximum number of errors have occurred (1 by default):
```
Own Mac: Interface=enp5s0, 70:b3:d5:19:50:04 dest:dc:a6:32:51:0e:e7
sent pkts:   983, errors/lost pkts:   0,   2.97 MByte/s
sent pkts:  1012, errors/lost pkts:   0,   3.06 MByte/s
sent pkts:  1011, errors/lost pkts:   0,   3.06 MByte/s
sent pkts:  1012, errors/lost pkts:   0,   3.06 MByte/s
sent pkts:  1004, errors/lost pkts:   0,   3.04 MByte/s
sent pkts:   997, errors/lost pkts:   0,   3.02 MByte/s
sent pkts:   997, errors/lost pkts:   0,   3.02 MByte/s
sent pkts:  1007, errors/lost pkts:   0,   3.05 MByte/s
^CStopped
Total Stats: sent pkts:  8501, errors/lost pkts:   0,   3.04 MByte/s
```

### How To...
#### Limit Runtime
Specify `-r` option, e.g. `-r 20` stops the test automatically after 20s.

#### Accept More Errors
Specify `-e` option to allow more than one error, e.g. `-e 100`.

#### Limit Used Bandwith
Specify `-d` option to add a delay between each ping to the peer machine. E.g. `-d 1000` adds one ms delay.

#### See More Error Details
Specify `-v`

#### Test Multiple NICs
The server can handle multiple clients. It just echoes what it receives. So you can have a single peer machine running the server and many clients with NICs under test.

## How it works

* Client sends a raw ethernet packet to the server.
    * Packet has a specific Etherent type (0xccdd), the maximum ethernet frame length (1518 bytes). The payload is just a 4-byte sequence number, and the rest is filled with zeroes.
* Client waits for server reply.
* When the server receives such a packet, it swaps source and destination MAC addresses and send the packet back.
    * The Server does not do any error checking
* When the Client has received the reply, it checks for correct header and sequence number
* The Client executes a delay if the `-d` option was given
