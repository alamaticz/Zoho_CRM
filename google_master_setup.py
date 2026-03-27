import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# SCOPE for Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    # Load your keys from environment variables
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    project_id = os.environ.get("GOOGLE_PROJECT_ID", "identifai-619c7")

    if not client_id or not client_secret:
        print("ERROR: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in environment.")
        return
    
    config = {
        "installed": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }
    
    # Desktop apps are 100% stable with port=0
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    creds = flow.run_local_server(port=0)
    
    print("\n" + "="*50)
    print("MASTER GENERATED SUCCESSFUL! 🏁")
    print("COPY THIS KEY TO YOUR .env AS 'GOOGLE_REFRESH_TOKEN':")
    print(f"\nGOOGLE_REFRESH_TOKEN='{creds.refresh_token}'")
    print("="*50 + "\n")

if __name__ == '__main__':
    main()
