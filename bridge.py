from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json
from pathlib import Path
from datetime import datetime

def connect_to(chain):
    if chain == 'source': # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet
    elif chain == 'destination': # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet
    else:
        raise ValueError("Unknown chain")
    
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3

def get_contract_info(chain, contract_info):
    try:
        with open(contract_info, 'r') as f:
            contracts = json.load(f)
    except Exception as e:
        print(f"Failed to read contract info\nPlease contact your instructor\n{e}")
        return None
    return contracts[chain]

def scan_blocks(chain, contract_info="contract_info.json"):
    if chain not in ['source','destination']:
        print(f"Invalid chain: {chain}")
        return 0

    # Connect to the two chains
    w3_source = connect_to('source')
    w3_dest = connect_to('destination')

    source_info = get_contract_info('source', contract_info)
    dest_info = get_contract_info('destination', contract_info)

    if source_info is None or dest_info is None:
        print("Failed to load contract info.")
        return 0

    # Load warden's private key
    warden_private_key = source_info['warden_private_key']  # Same warden for both sides
    warden_address = w3_source.eth.account.from_key(warden_private_key).address

    # Load ABIs
    source_abi = source_info['abi']
    dest_abi = dest_info['abi']

    # Load Contract instances
    source_contract = w3_source.eth.contract(address=source_info['address'], abi=source_abi)
    dest_contract = w3_dest.eth.contract(address=dest_info['address'], abi=dest_abi)

    # Find latest block numbers
    latest_source_block = w3_source.eth.get_block_number()
    latest_dest_block = w3_dest.eth.get_block_number()

    # Scan last 5 blocks on source for Deposit events
    print(f"Scanning Source (Avalanche) from blocks {latest_source_block-5} to {latest_source_block} for Deposit events...")
    deposit_events = source_contract.events.Deposit.create_filter(
        fromBlock=max(latest_source_block-5, 0),
        toBlock=latest_source_block
    ).get_all_entries()

    for event in deposit_events:
        print(f"Found Deposit event: {event.args}")

        token = event.args['token']
        recipient = event.args['recipient']
        amount = event.args['amount']

        # Build transaction to call wrap() on destination chain
        nonce = w3_dest.eth.get_transaction_count(warden_address)

        tx = dest_contract.functions.wrap(
            token,
            recipient,
            amount
        ).build_transaction({
            'chainId': 97, # BNB Testnet chainId
            'gas': 300000,
            'gasPrice': w3_dest.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = w3_dest.eth.account.sign_transaction(tx, private_key=warden_private_key)
        tx_hash = w3_dest.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Sent wrap() on Destination. TxHash: {tx_hash.hex()}")

    # Scan last 5 blocks on destination for Unwrap events
    print(f"Scanning Destination (BNB) from blocks {latest_dest_block-5} to {latest_dest_block} for Unwrap events...")
    unwrap_events = dest_contract.events.Unwrap.create_filter(
        fromBlock=max(latest_dest_block-5, 0),
        toBlock=latest_dest_block
    ).get_all_entries()

    for event in unwrap_events:
        print(f"Found Unwrap event: {event.args}")

        token = event.args['token']
        recipient = event.args['recipient']
        amount = event.args['amount']

        # Build transaction to call withdraw() on source chain
        nonce = w3_source.eth.get_transaction_count(warden_address)

        tx = source_contract.functions.withdraw(
            token,
            recipient,
            amount
        ).build_transaction({
            'chainId': 43113, # Avalanche Fuji Testnet chainId
            'gas': 3000000,
            'gasPrice': w3_source.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = w3_source.eth.account.sign_transaction(tx, private_key=warden_private_key)
        tx_hash = w3_source.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Sent withdraw() on Source. TxHash: {tx_hash.hex()}")
