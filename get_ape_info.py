from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# You will need the ABI to connect to the contract
# The file 'abi.json' has the ABI for the bored ape contract
# In general, you can get contract ABIs from etherscan
# https://api.etherscan.io/api?module=contract&action=getabi&address=0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D
with open('ape_abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
api_url = "https://eth-mainnet.g.alchemy.com/v2/6WRL-ZNSr68BV1oOgHnlkCUEelWK_9B7"  # YOU WILL NEED TO PROVIDE THE URL OF AN ETHEREUM NODE
provider = HTTPProvider(api_url)
web3 = Web3(provider)

# Ensure the connection to Ethereum node is established
if not web3.is_connected():
    raise Exception("Failed to connect to Ethereum node.")

# Connect to the Bored Ape Yacht Club contract
contract = web3.eth.contract(address=contract_address, abi=abi)

def get_ape_info(ape_id):
    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert 9999 >= ape_id, f"{ape_id} must be less than 10,000"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # YOUR CODE HERE

    try:
        # Get the owner address of the ape
        owner = contract.functions.ownerOf(ape_id).call()
        data['owner'] = owner
    except Exception as e:
        print(f"Error fetching owner for Ape {ape_id}: {e}")
        return data  # Return empty data on failure

    try:
        # Get the token URI for the ape
        token_uri = contract.functions.tokenURI(ape_id).call()

        # The token URI will give us the IPFS link to the metadata
        # The format will be something like: "ipfs://QmeSjSinHpPnmXmspMjwiXyN6zS4E9zccariGR3jxcaWtq/1"
        # Strip the "ipfs://" prefix
        ipfs_hash = token_uri.replace("ipfs://", "")

        # Access the metadata using an IPFS gateway
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        response = requests.get(ipfs_url)

        if response.status_code == 200:
            metadata = response.json()
            # Extract the image URI and eyes attribute from the metadata
            data['image'] = metadata.get('image', "")
            # Try to find the "eyes" attribute (assuming it's part of the metadata)
            for attribute in metadata.get('attributes', []):
                if 'Eyes' in attribute.get('trait_type', ''):
                    data['eyes'] = attribute.get('value', "")
        else:
            print(f"Failed to fetch metadata for Ape {ape_id}. Status code: {response.status_code}")

    except Exception as e:
        print(f"Error fetching metadata for Ape {ape_id}: {e}")

    assert isinstance(data, dict), f'get_ape_info{ape_id} should return a dict'
    assert all([a in data.keys() for a in
                ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"
    return data
