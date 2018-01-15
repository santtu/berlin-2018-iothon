#!/usr/bin/env python3
import argparse
import asyncio
from aiocoap import GET, PUT, Message, Context
import time
from urllib.parse import urljoin
from web3 import Web3, HTTPProvider
import json


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--coap-server', metavar='URL',
                        default="coap://localhost")

    parser.add_argument('--temperature-resource', default='temperature',
                        metavar='RESOURCE')
    parser.add_argument('--actuator-resource', default='actuator',
                        metavar='RESOURCE')

    parser.add_argument('--password', default="")
    parser.add_argument('contract', metavar='CONTRACT')
    parser.add_argument('account', metavar='ACCOUNT')

    parser.add_argument('--rpc-server', default='http://localhost:8545',
                        metavar='URL')
    parser.add_argument('--abi-file', default='device_sol_Device.abi',
                        metavar='FILE')

    parser.add_argument('--update-interval', type=int, default=5)
    parser.add_argument('--update-accuracy', type=int, default=1)

    args = parser.parse_args()

    web3 = Web3(HTTPProvider(args.rpc_server, request_kwargs={'timeout': 60}))
    abi = json.load(open(args.abi_file))
    device = web3.eth.contract(args.contract, abi=abi)
    client = await Context.create_client_context()

    def send_actuation(value):
        client.request(Message(
            code=PUT,
            payload=str(value).encode(),
            uri=urljoin(args.coap_server, args.actuator_resource)))

    async def get_temperature():
        response = await client.request(Message(
            code=GET,
            uri=urljoin(args.coap_server, args.temperature_resource))).response

        temp = float(response.payload.decode())
        return temp

    # Look up initial value and publish that, this handles restarts
    # without requiring a new actuation transaction
    old_actuation = device.call().actuation()
    send_actuation(old_actuation)

    # Retrieve current temperature
    old_temp = device.call().get() / 100.0

    while True:
        temp = await get_temperature()

        if ((round(temp, args.update_accuracy) !=
             round(old_temp, args.update_accuracy))):
            print("[interface] Updating temperature:", temp)
            temp_value = int(100 * (float(temp) + 0.005))
            web3.personal.unlockAccount(args.account, args.password)
            device.transact({"from": args.account}).set(temp_value)

        actuation = device.call().actuation()
        if actuation != old_actuation:
            print("[interface] Actuation:", actuation)
            send_actuation(actuation)

        old_temp = temp
        old_actuation = actuation

        time.sleep(args.update_interval)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
