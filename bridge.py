from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json

def connect_to(chain):
    if chain == 'source':  # Source chain is Avalanche
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'destination':  # Destination chain is BNB
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        raise ValueError(f"Unknown chain: {chain}")

    w3 = Web3(HTTPProvider(api_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3

def get_contract_info(chain, contract_info):
    with open(contract_info, 'r') as f:
        contracts = json.load(f)
    return contracts[chain]

def scan_blocks(chain, contract_info="contract_info.json"):
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    source_w3 = connect_to('source')
    dest_w3 = connect_to('destination')

    contracts = {
        'source': get_contract_info('source', contract_info),
        'destination': get_contract_info('destination', contract_info)
    }

    source_contract = source_w3.eth.contract(address=contracts['source']['address'], abi=contracts['source']['abi'])
    dest_contract = dest_w3.eth.contract(address=contracts['destination']['address'], abi=contracts['destination']['abi'])

    signing_key = contracts['source']['warden_key']

    if chain == 'source':
        latest_block = source_w3.eth.block_number
        start_block = max(latest_block - 5, 0)
        print(f"Scanning Source (Avalanche) from blocks {start_block} to {latest_block} for Deposit events...")

        try:
            deposit_events = source_contract.events.Deposit.create_filter(
                from_block=start_block,
                to_block=latest_block
            ).get_all_entries()

            for event in deposit_events:
                token = event.args['token']
                recipient = event.args['recipient']
                amount = event.args['amount']

                print(f"Found Deposit: token={token}, recipient={recipient}, amount={amount}")

                nonce = dest_w3.eth.get_transaction_count(Web3.to_checksum_address(contracts['destination']['warden_address']))
                txn = dest_contract.functions.wrap(token, recipient, amount).build_transaction({
                    'chainId': 97,  # BNB testnet
                    'gas': 50000,
                    'gasPrice': dest_w3.to_wei('12', 'gwei'),
                    'nonce': nonce,
                })

                signed_txn = dest_w3.eth.account.sign_transaction(txn, private_key=signing_key)
                tx_hash = dest_w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # fixed here
                print(f"Sent wrap() tx: {tx_hash.hex()}")

        except Exception as e:
            print(f"Error processing source events: {e}")

    elif chain == 'destination':
        latest_block = dest_w3.eth.block_number
        start_block = max(latest_block - 5, 0)
        print(f"Scanning Destination (BNB) from blocks {start_block} to {latest_block} for Unwrap events...")

        try:
            unwrap_events = dest_contract.events.Unwrap.create_filter(
                from_block=start_block,
                to_block=latest_block
            ).get_all_entries()

            for event in unwrap_events:
                token = event.args['token']
                recipient = event.args['recipient']
                amount = event.args['amount']

                print(f"Found Unwrap: token={token}, recipient={recipient}, amount={amount}")

                nonce = source_w3.eth.get_transaction_count(Web3.to_checksum_address(contracts['source']['warden_address']))
                txn = source_contract.functions.withdraw(token, recipient, amount).build_transaction({
                    'chainId': 43113,  # Avalanche Fuji testnet
                    'gas': 50000,
                    'gasPrice': source_w3.to_wei('25', 'gwei'),
                    'nonce': nonce,
                })

                signed_txn = source_w3.eth.account.sign_transaction(txn, private_key=signing_key)
                tx_hash = source_w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # fixed here
                print(f"Sent withdraw() tx: {tx_hash.hex()}")

        except Exception as e:
            print(f"Error processing destination events: {e}")

if __name__ == "__main__":
    scan_blocks('source')
    scan_blocks('destination')
