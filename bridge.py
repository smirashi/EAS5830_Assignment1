from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd
from eth_account import Account

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


def get_contract_info(chain, contract_info_file="contract_info.json"):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info_file, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return None
    return contracts[chain]


def scan_blocks(chain, contract_info_file="contract_info.json"):
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
        return

    contracts = get_contract_info(chain, contract_info_file)
    if not contracts:
        return

    w3 = connect_to(chain)
    if not w3.is_connected():
        print(f"Failed to connect to {chain} chain.")
        return

    if chain == 'source':
        contract_address = contracts['address']
        abi = contracts['abi']
        event_name = 'Deposit'
        other_chain = 'destination'
        call_function = 'wrap'
        arg_names = ['token', 'recipient', 'amount']
    elif chain == 'destination':
        contract_address = contracts['address']
        abi = contracts['abi']
        event_name = 'Unwrap'
        other_chain = 'source'
        call_function = 'withdraw'
        arg_names = ['token', 'recipient', 'amount']
    else:
        return

    contract = w3.eth.contract(address=contract_address, abi=abi)
    latest_block = w3.eth.get_block_number()
    start_block = max(0, latest_block - 5)

    event_filter = contract.events[event_name].create_filter(from_block=start_block, to_block=latest_block)
    events = event_filter.get_all_entries()

    if events:
        print(f"Found {len(events)} '{event_name}' events on {chain} chain (blocks {start_block} to {latest_block}).")
        other_w3 = connect_to(other_chain)
        other_contracts = get_contract_info(other_chain, contract_info_file)
        if not other_w3.is_connected() or not other_contracts:
            print(f"Failed to connect to {other_chain} chain or load contract info.")
            return

        other_contract_address = other_contracts['address']
        other_abi = other_contracts['abi']
        other_contract = other_w3.eth.contract(address=other_contract_address, abi=other_abi)
        warden_private_key = other_contracts.get('warden_private_key')

        if not warden_private_key:
            print(f"Warden private key not found for {other_chain} in contract_info.json")
            return

        warden_account = Account.from_key(warden_private_key)
        warden_address = warden_account.address

        for event in events:
            print(f"Processing {event_name} event on {chain}: {event.transactionHash.hex()}")
            try:
                args = event.args
                call_args = [args[arg] for arg in arg_names]

                nonce = other_w3.eth.get_transaction_count(warden_address)
                gas_price = other_w3.eth.gas_price
                tx = other_contract.functions[call_function](*call_args).build_transaction({
                    'chainId': other_w3.eth.chain_id,
                    'gas': 2000000,  # Adjust gas limit as needed
                    'gasPrice': gas_price,
                    'nonce': nonce,
                })
                signed_tx = warden_account.sign_transaction(tx)
                # Modified line to access raw transaction bytes
                tx_hash = other_w3.eth.send_raw_transaction(signed_tx.raw)
                print(f"Called '{call_function}' on {other_chain}, transaction hash: {tx_hash.hex()}")

            except Exception as e:
                print(f"Error processing {event_name} event and calling '{call_function}': {e}")

if __name__ == "__main__":
    scan_blocks('source')
    scan_blocks('destination')
