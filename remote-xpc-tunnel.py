import asyncio
import json
import logging
import argparse
import os

from cryptography.hazmat.primitives.asymmetric import rsa
from pymobiledevice3.cli.cli_common import prompt_device_list
from pymobiledevice3.cli.remote import get_device_list
from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.remote.core_device_tunnel_service import create_core_device_tunnel_service
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.remote.utils import resume_remoted_if_required, stop_remoted_if_required

parser = argparse.ArgumentParser(description='RemoteXPC Tunnel')
parser.add_argument("--list-remote-devices", help="List remote devices", action="store_true")
parser.add_argument("--device-udid", help="Device UDID")
parser.add_argument("--tunnels", type=int, help="Number of tunnels to create")
parser.add_argument("--close-tunnels-signal-file", help="Path of file used to force closing tunnels")
parser.add_argument("--rsd-destination-path", help="Path of remote addresses json")
remote_xpc_log = "Remote XPC Tunnel: "


def get_remote_devices():
    devices = get_device_list()
    if not devices:
        raise NoDeviceConnectedError()
    return devices


class RemoteXPC:
    def __init__(self, devices):
        self.devices = devices
        self.tunnels_to_create = 1
        self.close_tunnels_signal_file = None
        self.rsd_destination = None

    def create_tunnels(self, device_udid=None):
        if len(self.devices) == 1:
            # only one device found
            rsd = self.devices[0]
        else:
            # several devices were found
            if device_udid is None:
                # show prompt if non explicitly selected
                rsd = prompt_device_list(self.devices)
            else:
                rsd = [device for device in self.devices if device.udid == device_udid]
                print(rsd)
                if len(rsd) > 0:
                    rsd = rsd[0]
                else:
                    raise NoDeviceConnectedError()

        if device_udid is not None and rsd.udid != device_udid:
            raise NoDeviceConnectedError()

        asyncio.run(self.start_quic_tunnel_concurrently(rsd), debug=True)

    async def start_quic_tunnel_concurrently(self, rsd):
        tasks = [self.start_quic_tunnel(rsd) for _ in range(self.tunnels_to_create)]
        await asyncio.gather(*tasks)
        if self.close_tunnels_signal_file:
            logging.info(f"{remote_xpc_log} removing close tunnels signal file...")
            os.remove(self.close_tunnels_signal_file)

    async def start_quic_tunnel(self, service_provider: RemoteServiceDiscoveryService) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        stop_remoted_if_required()
        with create_core_device_tunnel_service(service_provider, autopair=True) as service:
            async with service.start_quic_tunnel(private_key, secrets_log_file=None) as tunnel_result:
                resume_remoted_if_required()
                logging.info(f"{remote_xpc_log} --rsd {tunnel_result.address} {tunnel_result.port}")
                if self.rsd_destination:

                    if os.path.exists(self.rsd_destination):
                        with open(self.rsd_destination, "r") as json_file:
                            existing_data = json.load(json_file)
                    else:
                        existing_data = []

                    new_data = [{
                        "address": tunnel_result.address,
                        "port": tunnel_result.port,
                        "available": True
                    }]

                    existing_data.extend(new_data)

                    with open(self.rsd_destination, "w") as json_file:
                        json.dump(existing_data, json_file, indent=4)

                if self.close_tunnels_signal_file:
                    while not os.path.exists(self.close_tunnels_signal_file):
                        # wait signal file existence while the asyncio tasks execute
                        await asyncio.sleep(.5)
                else:
                    while True:
                        # wait user input while the asyncio tasks execute
                        await asyncio.sleep(.5)


def main():
    if os.geteuid() != 0:
        logging.info(f"{remote_xpc_log} This script requires root privileges.")
        return

    logging.info(f"{remote_xpc_log} Running with root privileges")
    args = parser.parse_args()

    if not args:
        logging.info(f"{remote_xpc_log} No args were specified!")
        return

    devices = get_remote_devices()
    remote_xpc = RemoteXPC(devices)
    connected_devices = []
    if args.list_remote_devices:
        for device in remote_xpc.devices:
            connected_devices.append(device.udid)

        connected_devices = json.dumps(connected_devices)
        print(connected_devices)
        return

    if not args.device_udid:
        logging.info(f"{remote_xpc_log} No Device UDID found, use --device-udid arg")
        return

    if args.tunnels:
        remote_xpc.tunnels_to_create = args.tunnels
    else:
        logging.info(f"{remote_xpc_log} No tunnels were specified, default value will be used!")

    if args.close_tunnels_signal_file:
        remote_xpc.close_tunnels_signal_file = args.close_tunnels_signal_file
    else:
        logging.info(f"{remote_xpc_log} No close tunnels signal file specified, default value will be used!")

    if args.rsd_destination_path:
        remote_xpc.rsd_destination = args.rsd_destination_path
    else:
        logging.info(f"{remote_xpc_log} No rsd destination path specified, addresses will be just printed!")

    remote_xpc.create_tunnels()


if __name__ == "__main__":
    main()
