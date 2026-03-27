"""
ZOHO CRM ONE-TIME SETUP SCRIPT
================================
Run this script ONCE. After that, your main script will work forever.

STEP 1: Go to https://api-console.zoho.in
STEP 2: Click "Add Client" -> Choose "Self Client" -> Click "Create"
STEP 3: Copy the Client ID and Client Secret
STEP 4: Paste them below when this script asks
"""

import webbrowser
import urllib.parse
import json
import requests
import os

print("=" * 60)
print("ZOHO CRM ONE-TIME AUTH SETUP")
print("=" * 60)
print()
print("STEP 1: Open this link in your browser:")
print("  https://api-console.zoho.in")
print()
print("STEP 2: Click 'Add Client'")
print("STEP 3: Choose 'Self Client'")
print("STEP 4: Click 'CREATE'")
print("STEP 5: Copy the Client ID and Client Secret shown")
print()

client_id = input("Paste your CLIENT ID here: ").strip()
client_secret = input("Paste your CLIENT SECRET here: ").strip()

SCOPES = "ZohoCRM.modules.ALL,ZohoCRM.settings.ALL,ZohoCRM.users.READ,ZohoCRM.org.READ,ZohoCRM.notifications.ALL"

# Build authorization URL for India datacenter
auth_url = (
    f"https://accounts.zoho.in/oauth/v2/auth"
    f"?scope={urllib.parse.quote(SCOPES)}"
    f"&client_id={client_id}"
    f"&response_type=code"
    f"&access_type=offline"
    f"&redirect_uri=https://www.zoho.in"
)

print()
print("Opening your browser for authorization...")
print("When the browser opens:")
print("  1. Select 'Alamaticz Solutions' from the org list")
print("  2. Click 'Accept'")
print("  3. After accepting, your browser will redirect to zoho.in")
print("  4. Look at the URL in your browser address bar")
print("  5. Copy EVERYTHING after 'code=' and before '&'")
print()

webbrowser.open(auth_url)

print("Waiting for you to authorize...")
auth_code = input("Paste the CODE from the browser URL here: ").strip()

# Exchange code for tokens
print()
print("Getting your tokens...")

token_url = "https://accounts.zoho.in/oauth/v2/token"
payload = {
    "code": auth_code,
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": "https://www.zoho.in",
    "grant_type": "authorization_code"
}

response = requests.post(token_url, data=payload)
token_data = response.json()

if "refresh_token" not in token_data:
    print()
    print("ERROR: Could not get token. Response from Zoho:")
    print(token_data)
    print()
    print("Please run this script again.")
else:
    # Load existing config if it exists
    config_path = os.path.join(os.path.dirname(__file__), "zoho_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                config = json.load(f)
            except:
                config = {}
    else:
        config = {}
        
    # Update config with new auth tokens
    config.update({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": token_data["refresh_token"],
        "access_token": token_data.get("access_token", ""),
        "api_domain": "https://www.zohoapis.in"
    })
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print()
    print("=" * 60)
    print("SUCCESS! Your Zoho credentials have been saved.")
    print(f"Saved to: {config_path}")
    print()
    print("Now run your main script:")
    print("  python enterprise_mcp_processor.py")
    print("=" * 60)
