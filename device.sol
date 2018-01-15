// -*- javascript -*-

pragma solidity ^0.4.16;

contract Device {
    // store the value in 100th of kelvins, e.g. 0C is 27315
    uint private temperature;

    // actuator value
    uint private actuator;

    // owner of the contract, they are the one only able to set() the
    // temperature value
    address private owner;

    // payment required for setting the actuator
    uint constant price = 1000000; // 1 Mwei

    function Device() public {
        owner = msg.sender;
        temperature = 0;
    }

    event Measured(uint temperature);

    function set(uint t) public {
        require(msg.sender == owner);
        temperature = t;
        Measured(temperature);
    }

    function get() public view returns (uint) {
        return temperature;
    }

    event Actuated(uint actuation);

    function actuate(uint value) public payable {
        require(msg.value >= price);

        uint excess = msg.value - price;

        if (excess > 0)
            msg.sender.transfer(excess);

        actuator = value;
        Actuated(actuator);
    }

    function actuation() public view returns (uint) {
        return actuator;
    }
}
