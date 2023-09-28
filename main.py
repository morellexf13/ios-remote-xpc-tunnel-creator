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
from pymobiledevice3.remote.utils import resume_remoted_if_required, stop_remoted, stop_remoted_if_required

parser = argparse.ArgumentParser(description='RemoteXPC Tunnel')
parser.add_argument("--udid", type=str)
parser.add_argument("--log-destination-path", type=str)
parser.add_argument("--list-remote-devices", type=bool)
remote_xpc_log = "Remote XPC Tunnel: "


def get_remote_devices():
    devices = get_device_list()
    if not devices:
        raise NoDeviceConnectedError()
    return devices


def create_tunnel(udid=None, log_destination=None):
    devices = get_remote_devices()
    if len(devices) == 1:
        # only one device found
        rsd = devices[0]
    else:
        # several devices were found
        if udid is None:
            # show prompt if non explicitly selected
            rsd = prompt_device_list(devices)
        else:
            rsd = [device for device in devices if device.udid == udid]
            if len(rsd) > 0:
                rsd = rsd[0]
            else:
                raise NoDeviceConnectedError()

    if udid is not None and rsd.udid != udid:
        raise NoDeviceConnectedError()

    asyncio.run(start_quic_tunnel(rsd, log_destination), debug=True)


async def start_quic_tunnel(service_provider: RemoteServiceDiscoveryService, log_destination=None) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    stop_remoted_if_required()
    with create_core_device_tunnel_service(service_provider, autopair=True) as service:
        async with service.start_quic_tunnel(private_key, secrets_log_file=None) as tunnel_result:
            resume_remoted_if_required()
            logging.info(f"{remote_xpc_log} --rsd {tunnel_result.address} {tunnel_result.port}")
            if log_destination:
                with open(log_destination, "w") as log_file:
                    log_file.write(json.dumps({
                        "address": tunnel_result.address,
                        "port": tunnel_result.port
                    })) 
            while True:
                # wait user input while the asyncio tasks execute
                await asyncio.sleep(.5)


def main():

    if os.geteuid() != 0:
        logging.info(f"{remote_xpc_log} This script requires root privileges.")
        return

    logging.info(f"{remote_xpc_log} Running with root privileges")

    args = parser.parse_args()
    device_udid = args.udid
    log_destination_path = args.log_destination_path
    list_remote_devices = args.list_remote_devices

    connected_devices = []
    if list_remote_devices:
        devices = get_remote_devices()
        for device in devices:
            connected_devices.append(device.udid)
        
        connected_devices = json.dumps(connected_devices)
        print(connected_devices)
        return

    if not list_remote_devices and not log_destination_path:
        logging.info(f"{remote_xpc_log} No log destination path found!, use --log-destination-path arg")
        return

    if not device_udid:
        logging.info(f"{remote_xpc_log} Tunnel couldn't be created, use --udid arg to specify a device")
        return
    else:
        logging.info(f"{remote_xpc_log} Creating tunnel with device: {device_udid}...")
        create_tunnel(udid=device_udid, log_destination=log_destination_path)


if __name__ == "__main__":
    main()
