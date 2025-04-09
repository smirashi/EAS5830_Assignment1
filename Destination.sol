// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );
	event Creation( address indexed underlying_token, address indexed wrapped_token );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

  function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE
    require(underlying_tokens[_underlying_token] == address(0), "Token already registered");

    BridgeToken newToken = new BridgeToken(_underlying_token, name, symbol, address(this));
    newToken.grantRole(newToken.MINTER_ROLE(), address(this));

    address newTokenAddress = address(newToken);

    underlying_tokens[_underlying_token] = newTokenAddress;
    wrapped_tokens[newTokenAddress] = _underlying_token;
    tokens.push(newTokenAddress);

    emit Creation(_underlying_token, newTokenAddress);
    return newTokenAddress;
}

function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE
    address wrapped = underlying_tokens[_underlying_token];
    require(wrapped != address(0), "Token not registered");

    BridgeToken bridgeToken = BridgeToken(wrapped);
    bridgeToken.mint(_recipient, _amount);

    emit Wrap(_underlying_token, wrapped, _recipient, _amount);
}

function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
    address underlying = wrapped_tokens[_wrapped_token];
    require(underlying != address(0), "Token not registered");

    BridgeToken bridgeToken = BridgeToken(_wrapped_token);
    bridgeToken.burnFrom(msg.sender, _amount);

    emit Unwrap(underlying, _wrapped_token, msg.sender, _recipient, _amount);
	}

}
