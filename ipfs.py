import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	#YOUR CODE HERE
	PINATA_API_KEY = "eecfeacfa97d4564388a"
  	PINATA_SECRET_API_KEY = "f7e5f245f528450d57d1b4be70574e4a299cc3e387a473751962a071505fe493"
  	PINATA_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
  
  	headers = {
		"Content-Type": "application/json",
      		"pinata_api_key": PINATA_API_KEY,
      		"pinata_secret_api_key": PINATA_SECRET_API_KEY
      
  	}
    
  	response = requests.post(PINATA_URL, headers=headers, json={"pinataContent": data})
    
  	if response.status_code == 200:
		cid = response.json()["IpfsHash"]  # CID of the uploaded content
      	
  	else:
		raise Exception(f"Error: {response.text}")

	return cid
      

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
	#YOUR CODE HERE
	PINATA_GATEWAY_URL = f"https://gateway.pinata.cloud/ipfs/{cid}"
	
	response = requests.get(PINATA_GATEWAY_URL)

	if response.status_code == 200:
		data = json.loads(response.text)  # Convert back to Python dictionary
	else:
		raise Exception(f"Error: {response.text}")

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	
	return data

