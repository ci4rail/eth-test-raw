#
# Get MAC address of  a local interface
#
# Copyright (c) Ci4Rail GmbH
#
# Could have been done with fcntl(), but fcntl
# isn't available in all systems (e.g. missing in yocto)
#
import subprocess
import json


def get_mac_address(interface_name):
    cmd = ["ip", "-j", "link", "show", f"{interface_name}"]
    output = subprocess.check_output(cmd)
    values = json.loads(output)
    return values[0]["address"]


if __name__ == "__main__":
    print(get_mac_address("eth0"))
