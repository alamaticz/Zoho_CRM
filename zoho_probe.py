import asyncio, json, os, shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    with open('zoho_config.json', 'r') as f: config = json.load(f)
    mcp_script = os.path.abspath('alamaticz zoho mcp/dist/index.js')
    node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    
    server_params = StdioServerParameters(
        command=node_path, args=[mcp_script],
        env={**os.environ, "ZOHO_CLIENT_ID": config["client_id"], "ZOHO_CLIENT_SECRET": config["client_secret"], "ZOHO_REFRESH_TOKEN": config["refresh_token"], "ZOHO_API_DOMAIN": config["api_domain"], "ZOHO_ACCOUNTS_URL": "https://accounts.zoho.in"}
    )
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("\n🔍 FETCHING ZOHO FIELDS...")
            response = await session.call_tool("zohocrm_get_module_fields", arguments={"module": "Leads"})
            fields = json.loads(response.content[0].text)
            
            # Print field names to see which ones match our AI data
            print("\n✅ VALID ZOHO FIELDS:")
            for field in fields.get("fields", []):
                if field.get("field_label") in ["Monthly Income", "Phone", "Lead Source"]:
                    print(f"- {field.get('field_label')} -> API NAME: {field.get('api_name')}")

if __name__ == "__main__":
    asyncio.run(main())
