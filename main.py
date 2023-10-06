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
parser.add_argument("--udid", type=str)
parser.add_argument("--rsd-destination-path", type=str)
parser.add_argument("--list-remote-devices", type=bool)
parser.add_argument("--tunnels", type=int)
remote_xpc_log = "Remote XPC Tunnel: "


def get_remote_devices():
    devices = get_device_list()
    if not devices:
        raise NoDeviceConnectedError()
    return devices


class RemoteXPC:
    def __init__(self, devices):
        self.devices = devices

    def create_tunnels(self, device_udid=None, rsd_destination=None, quantity=1):
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

        asyncio.run(self.start_quic_tunnel_concurrently(rsd=rsd, rsd_destination=rsd_destination, quantity=quantity), debug=True)

    async def start_quic_tunnel_concurrently(self, rsd, rsd_destination, quantity):
        tasks = [self.start_quic_tunnel(rsd, rsd_destination) for _ in range(quantity)]
        await asyncio.gather(*tasks)

    async def start_quic_tunnel(self, service_provider: RemoteServiceDiscoveryService, rsd_destination=None) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        stop_remoted_if_required()
        with create_core_device_tunnel_service(service_provider, autopair=True) as service:
            async with service.start_quic_tunnel(private_key, secrets_log_file=None) as tunnel_result:
                resume_remoted_if_required()
                logging.info(f"{remote_xpc_log} --rsd {tunnel_result.address} {tunnel_result.port}")
                if rsd_destination:

                    if os.path.exists(rsd_destination):
                        with open(rsd_destination, "r") as json_file:
                            existing_data = json.load(json_file)
                    else:
                        existing_data = []

                    new_data = [{
                        "address": tunnel_result.address,
                        "port": tunnel_result.port,
                        "available": True
                    }]

                    existing_data.extend(new_data)

                    with open(rsd_destination, "w") as json_file:
                        json.dump(existing_data, json_file, indent=4)

                while True:
                    # wait user input while the asyncio tasks execute
                    await asyncio.sleep(.5)


def main():
    if os.geteuid() != 0:
        logging.info(f"{remote_xpc_log} This script requires root privileges.")
        return

    logging.info(f"{remote_xpc_log} Running with root privileges")

    connected_devices = []
    args = parser.parse_args()
    device_udid = args.udid
    rsd_destination_path = args.rsd_destination_path
    list_remote_devices = args.list_remote_devices
    tunnels = args.tunnels

    if not device_udid and not rsd_destination_path and not list_remote_devices:
        logging.info(f"{remote_xpc_log} No args were specified!")
        return

    devices = get_remote_devices()
    remote_xpc = RemoteXPC(devices)

    if list_remote_devices:
        for device in remote_xpc.devices:
            connected_devices.append(device.udid)

        connected_devices = json.dumps(connected_devices)
        print(connected_devices)
        return

    if device_udid and not rsd_destination_path:
        logging.info(f"{remote_xpc_log} No rsd destination path found!, use --rsd-destination-path arg")
        return

    if not device_udid:
        logging.info(f"{remote_xpc_log} Tunnel couldn't be created, use --udid arg to specify a device")
        return
    else:
        logging.info(f"{remote_xpc_log} Creating tunnel/s with device: {device_udid}...")
        remote_xpc.create_tunnels(device_udid=device_udid, rsd_destination=rsd_destination_path, quantity=tunnels)


if __name__ == "__main__":
    main()
