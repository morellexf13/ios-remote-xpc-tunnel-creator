import asyncio
import os
import argparse
from cryptography.hazmat.primitives.asymmetric import rsa
from pymobiledevice3.cli.cli_common import prompt_device_list
from pymobiledevice3.cli.remote import get_device_list
from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.remote.core_device_tunnel_service import create_core_device_tunnel_service
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService

parser = argparse.ArgumentParser(description='RemoteXPC Tunnel')
parser.add_argument("--udid", type=str)


def start_remote_xpc_tunnel(udid=None, secrets=None):
    devices = get_device_list()
    print(devices)  # debug
    if not devices:
        # no devices were found
        raise NoDeviceConnectedError()
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

    asyncio.run(start_quic_tunnel(rsd, secrets), debug=True)


async def start_quic_tunnel(service_provider: RemoteServiceDiscoveryService, secrets) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with create_core_device_tunnel_service(service_provider, autopair=True) as service:
        async with service.start_quic_tunnel(private_key, secrets_log_file=secrets) as tunnel_result:
            if secrets is not None:
                print("secrets")

            print(tunnel_result)
            # Shows rsd to use
            print(f'--rsd {tunnel_result.address} {tunnel_result.port}')

            while True:
                # wait user input while the asyncio tasks execute
                await asyncio.sleep(.5)


def main():

    if os.geteuid() != 0:
        print("This script requires root privileges.")
        return

    print("Running with root privileges")

    args = parser.parse_args()
    device_udid = args.udid

    if not device_udid:
        print("No device found, use --udid arg")
    else:
        print(f"Creating tunnel with device: {device_udid}...")
        start_remote_xpc_tunnel(udid=device_udid)


if __name__ == "__main__":
    main()
