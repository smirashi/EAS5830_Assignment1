from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd
import os


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]


def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return 0
    
        #YOUR CODE HERE
    contracts_info = get_contract_info(chain, contract_info)
    w3 = connect_to(chain)
    contract_address = w3.to_checksum_address(contracts_info['address'])
    abi = contracts_info['abi']
    contract = w3.eth.contract(address=contract_address, abi=abi)

    if chain == 'source':
        other_chain = 'destination'
        event_name = 'Deposit'
        function_name = 'wrap'
    elif chain == 'destination':
        other_chain = 'source'
        event_name = 'Unwrap'
        function_name = 'withdraw'

    other_contracts_info = get_contract_info(other_chain, contract_info)
    w3_other = connect_to(other_chain)
    other_contract_address = w3_other.to_checksum_address(other_contracts_info['address'])
    other_contract_abi = other_contracts_info['abi']
    other_contract = w3_other.eth.contract(address=other_contract_address, abi=other_contract_abi)

    deployer_key = os.environ.get('cf60bcbd511f92e9d4104b8116483e2496ed8456f0152e854b15346b227ebd2b')
    if not deployer_key:
        print("Error: DEPLOYER_PRIVATE_KEY environment variable not set.")
        return

    deployer_account = w3.eth.account.from_key(deployer_key)

    latest_block = w3.eth.block_number
    start_block = max(0, latest_block - 5)

    events = contract.events[event_name].get_logs(fromBlock=start_block, toBlock='latest')

    for event in events:
        print(f"Found {event_name} event on {chain}: {event.args}")
        if chain == 'source' and event_name == 'Deposit':
            token_address = event.args.erc20
            amount = event.args.amount
            recipient = event.args.recipient
            try:
                tx = other_contract.functions.wrap(token_address, amount, recipient).build_transaction({
                    'gas': 200000,
                    'gasPrice': w3_other.eth.gas_price,
                    'nonce': w3_other.eth.get_transaction_count(deployer_account.address),
                })
                signed_tx = w3_other.eth.account.sign_transaction(tx, deployer_key)
                tx_hash = w3_other.eth.send_raw_transaction(signed_tx.rawTransaction)
                print(f"Called wrap on {other_chain}. Transaction hash: {tx_hash.hex()}")
            except Exception as e:
                print(f"Error calling wrap: {e}")
        elif chain == 'destination' and event_name == 'Unwrap':
            token_address = event.args.erc20;
            amount = event.args.amount
            recipient = event.args.recipient
            try:
                tx = contract.functions.withdraw(token_address, amount, recipient).build_transaction({
                    'gas': 200000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': w3.eth.get_transaction_count(deployer_account.address),
                })
                signed_tx = w3.eth.account.sign_transaction(tx, deployer_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                print(f"Called withdraw on {other_chain}. Transaction hash: {tx_hash.hex()}")
            except Exception as e:
                print(f"Error calling withdraw: {e}")
