import requests
import json


def pin_to_ipfs(data):
    assert isinstance(data, dict), f"Error pin_to_ipfs expects a dictionary"
    # YOUR CODE HERE
    pinata_api_key = "eecfeacfa97d4564388a"
    pinata_secret_api_key = "f7e5f245f528450d57d1b4be70574e4a299cc3e387a473751962a071505fe493"
    pinata_url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": pinata_api_key,
        "pinata_secret_api_key": pinata_secret_api_key
    }

    response = requests.post(pinata_url, headers=headers,
                             json={"pinataContent": data})

    if response.status_code == 200:
        cid = response.json()["IpfsHash"]  # CID of the uploaded content
    else:
        raise Exception(f"Error: {response.text}")

    return cid


def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid,
                      str), f"get_from_ipfs accepts a cid in the form of a string"
    # YOUR CODE HERE
    pinata_gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"

    response = requests.get(pinata_gateway_url)

    if response.status_code == 200:
        data = json.loads(response.text)  # Convert back to Python dictionary
    else:
        raise Exception(f"Error: {response.text}")

    assert isinstance(data, dict), f"get_from_ipfs should return a dict"
    return data
