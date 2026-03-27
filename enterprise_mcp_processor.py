import os
import time
import json
import logging
import asyncio
import traceback
import sys
import shutil
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from groq import Groq
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import requests

# ============================================================
# PRODUCTION MISSION CORE: LEAD NEXUS ARCHITECTURE
# ============================================================

SYSTEM_PROMPT_CLEANING = """
You are a transcript cleaning tool. You have ONE job only: remove filler words.

REMOVE ONLY THESE:
- um, uh, ah, oh, hmm, haan, acha, okay okay, yeah yeah, so so

RESTORE THESE ALWAYS:
- "newly login" or "new lead" → new lead login

STRICT RULES:
1. ANTI-POLITE MANDATE: NEVER add "Thank you", "Watching", "Goodbye", or any polite closing.
2. MECHANICAL STOP: Stop exactly where the user stopped. 
3. DURATION MANDATE: Even if the transcript is only 1 or 2 words long, you MUST return the cleaned version.
4. PIN-TO-PIN: Do not change words with meaning.
5. Return only cleaned transcript.
"""

SYSTEM_PROMPT_EXTRACTION = """You are an Autonomous Senior Zoho CRM Architect & Data Auditor. 
Your task is to analyze the literal transcript, extract data, and assess quality.

AUDITOR PROTOCOLS:
- Confidence_Score: Rate the clarity of the lead data from 0-100.
- Needs_Review: Set to TRUE if:
  * Last_Name is 'Unknown'.
  * Requested_Loan_Amount is missing.
  * The transcript is too noisy/brief to confirm intent.

ZERO-LOSS MANDATE:
- NEVER add "Thank you for watching" or pleasantries.
- Stop exactly where the transcript ends.

EXTRACTION RULES:
1. ENTITY IDENTIFICATION: Identify subject as 'Last_Name'. Agent is ignored.
2. DYNAMIC FIELD CLASSIFICATION: Individual vs Corporate.
3. FINANCIAL PRECISION: Numbers as strings.
4. LEAD SOURCE/STATUS: Strict dropdown values.

OUTPUT SCHEMA (JSON):
{
  "First_Name": "string or null",
  "Last_Name": "string",
  "Type_of_Customer": "Individual or Corporate",
  "Phone": "string or null",
  "Email": "string or null",
  "Occupation": "Salaried/Self-Employed/Business",
  "Monthly_Income": "numeric string",
  "Organisation": "string",
  "Company": "string",
  "Loan_Type": "string",
  "Requested_Loan_Amount": "numeric string",
  "Lead_Source": "External Referral/Employee Referral/Field Activity/Flyer/Hoardings",
  "Referred_By": "name/source context",
  "Campaign_Source": "org/group context",
  "Lead_Status": "New",
  "Confidence_Score": 0-100,
  "Needs_Review": "Boolean",
  "Description": "Professional summary",
  "zoho_note": "Reasoning + Literal Transcript"
}
"""

# ============================================================
# CONFIGURATION & PATHS
# ============================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnterpriseProcessor")

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
INCOMING_DIR = BASE_DIR / "incoming"
PROCESSED_DIR = BASE_DIR / "processed"
ZOHO_CONFIG_FILE = BASE_DIR / "zoho_config.json"

for d in [INCOMING_DIR, PROCESSED_DIR]: os.makedirs(d, exist_ok=True)

def load_groq_client():
    try:
        key_file = BASE_DIR / "groq_key.txt"
        if not key_file.exists(): return None
        with open(key_file, "r") as f: return Groq(api_key=f.read().strip())
    except: return None

groq_client = load_groq_client()

# ============================================================
# ZOHO MCP CLIENT (Senior Architect Mode)
# ============================================================
class ZohoMcpManager:
    def _get_config(self):
        try:
            with open(ZOHO_CONFIG_FILE, 'r') as f: return json.load(f)
        except: return None

    async def process_to_zoho(self, transcript, filename):
        config = self._get_config()
        if not config or not groq_client: return False
            
        mcp_script_path = BASE_DIR / "alamaticz zoho mcp" / "dist" / "index.js"
        node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        
        # 1. AI Extraction (Senior Architect Auditor Mode)
        extract_res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACTION},
                {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(extract_res.choices[0].message.content)
        
        # 2. Field Mapping (Architect Auditor Sync)
        needs_review = data.get("Needs_Review")
        base_status = "Needs Review" if needs_review else data.get("Lead_Status", "New")
        
        zoho_data = {
            "First_Name": data.get("First_Name"),
            "Last_Name": data.get("Last_Name") or "Inquiry",
            "Phone": data.get("Phone"),
            "Email": data.get("Email"),
            "Lead_Status": base_status,
            "Lead_Source": data.get("Lead_Source"),
            "Type_of_Customer": data.get("Type_of_Customer"),
            "Loan_Type": data.get("Loan_Type"),
            "Loan_Budget": data.get("Requested_Loan_Amount"),
            "Monthly_Income": data.get("Monthly_Income"),
            "Company": data.get("Organisation") or data.get("Company") or "Private Individual",
            "Description": f"CONFIDENCE: {data.get('Confidence_Score')}% | AUDIT: {'REVIEWS REQ' if needs_review else 'CLEAR'}\n\n{data.get('Description')}"
        }
        
        final_payload = {k: v for k, v in zoho_data.items() if v is not None}

        # 3. Secure Sync via MCP
        server_params = StdioServerParameters(
            command=node_path,
            args=[str(mcp_script_path)],
            env={
                **os.environ,
                "ZOHO_CLIENT_ID": config.get("client_id", ""),
                "ZOHO_CLIENT_SECRET": config.get("client_secret", ""),
                "ZOHO_REFRESH_TOKEN": config.get("refresh_token", ""),
                "ZOHO_API_DOMAIN": config.get("api_domain", "https://www.zohoapis.in"),
                "ZOHO_ACCOUNTS_URL": "https://accounts.zoho.in"
            }
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.call_tool("zohocrm_upsert_records", arguments={
                    "module": "Leads", "data": [final_payload], "duplicate_check_fields": ["Phone"]
                })
                
                try:
                    res_json = json.loads(response.content[0].text)
                    record_id = res_json.get("data", [{}])[0].get("details", {}).get("id")
                    
                    if record_id:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        await session.call_tool("zohocrm_create_records", arguments={
                            "module": "Notes",
                            "data": [{
                                "Parent_Id": {"id": record_id},
                                "Note_Title": f"LEAD NEXUS ANALYSIS ({timestamp})",
                                "Note_Content": data.get("zoho_note", transcript),
                                "se_module": "Leads"
                            }]
                        })
                        logger.info(f"✅ Lead Created/Updated: {record_id}. Note Attached.")
                        return True
                except: return False
        return False

# ============================================================
# PROCESSING ENGINE
# ============================================================
PROCESSING_SET = set()

def transcribe_audio(file_path):
    if not groq_client: return None
    logger.info(f"🎤 Stage 1: Universal Translator Mode: {file_path.name}")
    try:
        # Step 1: Universal Translator (Option B + C Combined)
        with open(file_path, "rb") as audio_file:
            raw_text = groq_client.audio.translations.create(
                file=(file_path.name, audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
                temperature=0,
                prompt="interest rate, EMI, ROI, income, loan amount, lead login"
            )
        
        logger.info("🎤 Stage 2: Mechanical Eraser cleaning...")
        clean_res = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT_CLEANING}, {"role": "user", "content": raw_text}],
            model="llama-3.3-70b-versatile",
            temperature=0
        )
        return clean_res.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation Error: {e}")
        return None

def wait_for_file_release(file_path, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with open(file_path, 'rb'): return True
        except: time.sleep(1)
    return False

async def handle_audio_file(file_path, loop):
    if not file_path.exists(): return
    abs_path = str(file_path.resolve())
    if abs_path in PROCESSING_SET: return
    PROCESSING_SET.add(abs_path)
    
    logger.info(f"==== START PROCESSING: {file_path.name} ====")
    try:
        if not wait_for_file_release(file_path): return
        clean_text = transcribe_audio(file_path)
        if not clean_text: return
        
        dest = PROCESSED_DIR / file_path.name
        shutil.copy2(file_path, dest)
        try: file_path.unlink()
        except: pass
        
        mcp = ZohoMcpManager()
        await mcp.process_to_zoho(clean_text, file_path.name)
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        PROCESSING_SET.discard(abs_path)

class AudioHandler(FileSystemEventHandler):
    def __init__(self, loop): self.loop = loop
    def on_created(self, event):
        path = Path(event.src_path)
        if not event.is_directory and path.suffix.lower() in ('.ogg', '.mp3', '.wav'):
            asyncio.run_coroutine_threadsafe(handle_audio_file(path, self.loop), self.loop)

async def run_main():
    print(f"============================================================")
    print(f"ENTERPRISE ZOHO MCP TRANSLATOR (PID: {os.getpid()})")
    print(f"Monitoring: {INCOMING_DIR}")
    print(f"============================================================")
    loop = asyncio.get_running_loop()
    event_handler = AudioHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
    observer.start()
    try:
        while True:
            for f in INCOMING_DIR.glob("*"):
                if f.suffix.lower() in ('.ogg', '.mp3', '.wav'):
                    asyncio.run_coroutine_threadsafe(handle_audio_file(f, loop), loop)
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    try: asyncio.run(run_main())
    except KeyboardInterrupt: pass
