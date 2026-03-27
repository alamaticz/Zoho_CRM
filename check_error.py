import asyncio
import os
import shutil
import json
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

BASE_DIR = Path(r"c:\Users\hima7\OneDrive\Desktop\project\CRM claude cowork")

async def test_zoho_error():
    config_file = BASE_DIR / "zoho_config.json"
    with open(config_file, 'r') as f:
        config = json.load(f)

    mcp_script_path = BASE_DIR / "alamaticz zoho mcp" / "dist" / "index.js"
    node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    
    api_domain = config.get("api_domain", "https://www.zohoapis.in")
    accounts_url = "https://accounts.zoho.in" if ".in" in api_domain else "https://accounts.zoho.com"

    server_params = StdioServerParameters(
        command=node_path,
        args=[str(mcp_script_path)],
        env={
            **os.environ,
            "ZOHO_CLIENT_ID": config.get("client_id", ""),
            "ZOHO_CLIENT_SECRET": config.get("client_secret", ""),
            "ZOHO_REFRESH_TOKEN": config.get("refresh_token", ""),
            "ZOHO_API_DOMAIN": api_domain,
            "ZOHO_ACCOUNTS_URL": accounts_url
        }
    )

    fields_to_test = [
        {"Last_Name": "KarthikTest4", "Monthly_Income": 110000},
        {"Last_Name": "KarthikTest5", "Monthly_Income": "110000"},
        {"Last_Name": "KarthikTest6", "Company": "Casa Grand"},
        {"Last_Name": "KarthikTest7", "Organisation": "Casa Grand"},
    ]

    print("Connecting to MCP...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Calling create_records...")
            for i, data in enumerate(fields_to_test):
                try:
                    response = await session.call_tool("zohocrm_create_records", arguments={
                        "module": "Leads",
                        "data": [data]
                    })
                    res_text = response.content[0].text if response.content else ""
                    print(f"Test {i+1} SUCCESS: {list(data.keys())} -> {res_text[:50]}")
                except Exception as e:
                    print(f"Test {i+1} FAILED: {list(data.keys())} -> {e}")

if __name__ == "__main__":
    asyncio.run(test_zoho_error())
