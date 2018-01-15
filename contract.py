#!/usr/bin/env python3
import argparse
import time
from web3 import Web3, HTTPProvider
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--password', default="")
    parser.add_argument('contract', metavar='CONTRACT')
    parser.add_argument('account', metavar='ACCOUNT', nargs='?',
                        help='Required if --set-actuation is used')
    parser.add_argument('--amount', type=int, default=1000000000)

    parser.add_argument('--server-url', default='http://localhost:8545',
                        metavar='URL')
    parser.add_argument('--abi-file', default='device_sol_Device.abi',
                        metavar='FILE')

    parser.add_argument('--set-actuation', dest='actuation',
                        metavar='VALUE', type=int, default=None)

    args = parser.parse_args()

    web3 = Web3(HTTPProvider(args.server_url, request_kwargs={'timeout': 60}))
    abi = json.load(open(args.abi_file))
    device = web3.eth.contract(args.contract, abi=abi)

    # fetch current temperature and actuation values

    temp = device.call().get()
    act = device.call().actuation()

    print("Current temperature:", temp / 100.0)
    print("Current actuation:", act)

    if args.actuation is not None:
        assert args.account is not None, \
            "ACCOUNT may not be empty if --set is used"
        web3.personal.unlockAccount(args.account, args.password)
        device.transact({"from": args.account,
                         "value": args.amount}).actuate(args.actuation)
        print("Updated actuation to:", args.actuation)


if __name__ == '__main__':
    main()
