from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd
from eth_account import Account
from rlp import encode

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


def process_deposit(w3_dest, dest_contract, warden_account, deposit_event):
    """
    Processes a Deposit event by calling the wrap function on the destination chain.
    """
    token = deposit_event['args']['token']
    recipient = deposit_event['args']['recipient']
    amount = deposit_event['args']['amount']
    tx_hash_source = deposit_event['transactionHash'].hex()

    print(f"Processing Deposit event on source: {tx_hash_source}")

    try:
        nonce = w3_dest.eth.get_transaction_count(warden_account.address)
        gas_price = int(w3_dest.eth.gas_price)
        tx = dest_contract.functions.wrap(token, recipient, amount).build_transaction({
            'chainId': w3_dest.eth.chain_id,
            'gas': 2000000,  # Adjust gas limit as needed
            'gasPrice': gas_price,
            'nonce': nonce,
        })
        signed_tx = warden_account.sign_transaction(tx)
        raw_tx = encode(signed_tx)
        tx_hash_dest = w3_dest.eth.send_raw_transaction(raw_tx).hex()
        print(f"Called 'wrap' on destination, transaction hash: {tx_hash_dest}")
    except Exception as e:
        print(f"Error processing Deposit event and calling 'wrap': {e}")


def process_unwrap(w3_source, source_contract, warden_account, unwrap_event):
    """
    Processes an Unwrap event by calling the withdraw function on the source chain.
    """
    token = unwrap_event['args']['underlying_token']
    recipient = unwrap_event['args']['to']
    amount = unwrap_event['args']['amount']
    tx_hash_dest = unwrap_event['transactionHash'].hex()

    print(f"Processing Unwrap event on destination: {tx_hash_dest}")

    try:
        nonce = w3_source.eth.get_transaction_count(warden_account.address)
        gas_price = int(w3_source.eth.gas_price)
        tx = source_contract.functions.withdraw(token, recipient, amount).build_transaction({
            'chainId': w3_source.eth.chain_id,
            'gas': 2000000,  # Adjust gas limit as needed
            'gasPrice': gas_price,
            'nonce': nonce,
        })
        signed_tx = warden_account.sign_transaction(tx)
        raw_tx = encode(signed_tx)
        tx_hash_source = w3_source.eth.send_raw_transaction(raw_tx).hex()
        print(f"Called 'withdraw' on source, transaction hash: {tx_hash_source}")
    except Exception as e:
        print(f"Error processing Unwrap event and calling 'withdraw': {e}")


def scan_blocks(chain, contract_info_file="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scans for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain.
        When Deposit events are found, it calls the 'wrap' function on the destination chain.
        When Unwrap events are found, it calls the 'withdraw' function on the source chain.
    """
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
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
    elif chain == 'destination':
        contract_address = contracts['address']
        abi = contracts['abi']
        event_name = 'Unwrap'
        other_chain = 'source'
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

        for event in events:
            if chain == 'source':
                process_deposit(other_w3, other_contract, warden_account, event)
            elif chain == 'destination':
                source_contracts = get_contract_info('source', contract_info_file)
                if source_contracts:
                    w3_source = connect_to('source')
                    source_contract_address = source_contracts['address']
                    source_abi = source_contracts['abi']
                    source_contract = w3_source.eth.contract(address=source_contract_address, abi=source_abi)
                    process_unwrap(w3_source, source_contract, warden_account, event)
                else:
                    print("Could not load source contract info for processing Unwrap event.")

if __name__ == "__main__":
    scan_blocks('source')
    scan_blocks('destination')
