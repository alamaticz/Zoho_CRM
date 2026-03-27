import requests, json, os

CLIENT_ID = "1000.KF0ELTZOWIBYZEJADK5LZ7FELJRX6C"
CLIENT_SECRET = "c57d2d2d4e66cef6b7e8369fe49a0536a135b721d0"
GRANT_TOKEN = "1000.0d22a5870fd6323d86213bfbdd0b20bd.bd97bd5cebb260cf8be27b4ec89cf929"

response = requests.post(
    "https://accounts.zoho.in/oauth/v2/token",
    data={
        "code": GRANT_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": "https://www.zoho.in",
        "grant_type": "authorization_code"
    }
)

data = response.json()
print("Response:", json.dumps(data, indent=2))

if "refresh_token" in data:
    # Load existing config if it exists
    config_path = os.path.join(os.path.dirname(__file__), "zoho_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                existing_config = json.load(f)
            except:
                existing_config = {}
    else:
        existing_config = {}

    # Update config with new auth tokens
    existing_config.update({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": data["refresh_token"],
        "access_token": data.get("access_token", ""),
        "api_domain": "https://www.zohoapis.in"
    })
    
    with open(config_path, "w") as f:
        json.dump(existing_config, f, indent=2)
    print("\nSUCCESS! Tokens saved to zoho_config.json")
else:
    print("\nFAILED. Check the response above.")
