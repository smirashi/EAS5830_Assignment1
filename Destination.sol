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
    require(_underlying_token != address(0), "Invalid underlying token address");

       // Ensure that the token doesn't already exist
       require(wrapped_tokens[_underlying_token] == address(0), "Wrapped token already exists");

       // Deploy a new BridgeToken with the given parameters
       BridgeToken bridgeToken = new BridgeToken(_underlying_token, name, symbol, msg.sender);

       // Map the underlying token to the new wrapped token
       underlying_tokens[address(bridgeToken)] = _underlying_token;
       wrapped_tokens[_underlying_token] = address(bridgeToken);
       
       // Emit the Creation event
       emit Creation(_underlying_token, address(bridgeToken));

       return address(bridgeToken);
	}

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE
		// Get the wrapped token for the underlying token
    		address wrappedToken = wrapped_tokens[_underlying_token];
    		require(wrappedToken != address(0), "Wrapped token not registered");

    		// Mint the wrapped tokens to the recipient
    		BridgeToken(wrappedToken).mint(_recipient, _amount);

    		// Emit the Wrap event
    		emit Wrap(_underlying_token, wrappedToken, _recipient, _amount);
    
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
		// Get the underlying token for the wrapped token
    		address underlyingToken = underlying_tokens[_wrapped_token];
    		require(underlyingToken != address(0), "Underlying token not registered");

    		// Burn the wrapped tokens from the caller's address
    		BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

    		// Emit the Unwrap event
    		emit Unwrap(underlyingToken, _wrapped_token, msg.sender, _recipient, _amount);
}
