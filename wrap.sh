#!/bin/sh
cat <<EOF
var deviceContract = eth.contract($(cat device_sol_Device.abi));
var device = deviceContract.new({from: eth.accounts[0], gas:500000, data: "0x$(cat device_sol_Device.bin)"});
EOF
