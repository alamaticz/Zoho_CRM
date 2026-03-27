import os
import json
import logging
import shutil
import asyncio
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

# Google Drive API Imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Zoho MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ============================================================
# CONFIGURATION & PROMPTS
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExpertAdminAPI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZOHO_CONFIG_FILE = os.path.join(BASE_DIR, "zoho_config.json")


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

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers (Environment and API Clients)
def get_env_var(key):
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.lstrip().startswith(key):
                    idx_eq = line.find("=")
                    idx_col = line.find(":")
                    sep_idx = min(i for i in [idx_eq, idx_col] if i != -1)
                    val = line[sep_idx+1:].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    return val
    except: return None
    return None

def load_groq_client():
    try:
        with open("groq_key.txt", "r") as f:
            return Groq(api_key=f.read().strip())
    except: return None

AUDIO_FOLDER_ID = get_env_var("GOOGLE_DRIVE_AUDIO_FOLDER_ID")
TEXT_FOLDER_ID = get_env_var("GOOGLE_DRIVE_TEXT_FOLDER_ID")

# ============================================================
# GOOGLE DRIVE ENGINE
# ============================================================
def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive.file']
    client_id = get_env_var("GOOGLE_CLIENT_ID")
    client_secret = get_env_var("GOOGLE_CLIENT_SECRET")
    refresh_token = get_env_var("GOOGLE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]): return None
        
    try:
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret, scopes=scopes
        )
        creds.refresh(GoogleRequest())
        return build('drive', 'v3', credentials=creds)
    except: return None

def upload_to_drive(file_path, folder_id, content_type='application/octet-stream'):
    try:
        service = get_drive_service()
        if not service: return None
        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype=content_type)
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id',
            supportsAllDrives=True, supportsTeamDrives=True
        ).execute()
        return file.get('id')
    except: return None

groq_client = load_groq_client()

# ============================================================
# ZOHO PIPELINE ENGINE (Advanced Logic)
# ============================================================
async def push_to_zoho(transcript):
    if not groq_client: return None
    try:
        with open(ZOHO_CONFIG_FILE, 'r') as f: config = json.load(f)
        
        # 1. AI Extraction (Senior Architect Mode)
        logger.info("Extracting Structured Intelligence from Transcript...")
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
        
        # 2. Logic Mapping (AI Fields -> Zoho CRM Fields)
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
        
        # Final Payload Cleanup
        allowed_fields = [
            "First_Name", "Last_Name", "Lead_Status", "Lead_Source", "Type_of_Customer", 
            "Loan_Type", "Monthly_Income", "Loan_Budget", "Description", "Phone", "Email", "Company"
        ]
        final_payload = {k: v for k, v in zoho_data.items() if k in allowed_fields and v is not None}
        
        # 3. Secure Sync via MCP
        mcp_script = os.path.join(BASE_DIR, "alamaticz zoho mcp", "dist", "index.js")
        node_path = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        
        server_params = StdioServerParameters(
            command=node_path, args=[mcp_script],
            env={
                **os.environ, 
                "ZOHO_CLIENT_ID": config["client_id"], 
                "ZOHO_CLIENT_SECRET": config["client_secret"], 
                "ZOHO_REFRESH_TOKEN": config["refresh_token"], 
                "ZOHO_API_DOMAIN": "https://www.zohoapis.in",
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
                        # Attach the ADVANCED STRATEGIC NOTE
                        await session.call_tool("zohocrm_create_records", arguments={
                            "module": "Notes", 
                            "data": [{
                                "Parent_Id": {"id": record_id}, 
                                "Note_Title": f"LEAD NEXUS ANALYSIS {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                "Note_Content": data.get("zoho_note", transcript), 
                                "$se_module": "Leads"
                            }]
                        })
                    return record_id
                except: return None
    except Exception as e:
        logger.error(f"Zoho Sync Failed: {e}")
        return None

# ============================================================
# ENDPOINTS
# ============================================================
@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    temp_path = f"incoming/{file.filename}"
    os.makedirs("incoming", exist_ok=True)
    with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    
    with open(temp_path, "rb") as audio_file:
        # Stage 1: Advanced Whisper dictionary
        # Stage 1: Universal Translator Mode (Option B + C)
        raw_text = groq_client.audio.translations.create(
            file=(file.filename, audio_file.read()), 
            model="whisper-large-v3", 
            response_format="text",
            temperature=0,
            prompt="interest rate, EMI, ROI, income, loan amount, lead login"
        )
    
    logger.info(f"RAW WHISPER TEXT: {raw_text}")
    
    # Stage 2: Mechanical Eraser Cleaning
    clean_res = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT_CLEANING}, {"role": "user", "content": raw_text}],
        model="llama-3.3-70b-versatile",
        temperature=0
    )
    clean_text = clean_res.choices[0].message.content.strip()

    # Stage 4: Logical Archive
    upload_to_drive(temp_path, AUDIO_FOLDER_ID, file.content_type)
    
    return {"filename": file.filename, "transcript": clean_text}

class TranscriptSubmission(BaseModel):
    transcript: str
    filename: str

@app.post("/submit-to-zoho")
async def final_submit(sub: TranscriptSubmission):
    # Drive Upload
    audio_path = f"incoming/{sub.filename}"
    txt_path = f"verified_transcripts/final_{int(datetime.now().timestamp())}.txt"
    os.makedirs("verified_transcripts", exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f: f.write(sub.transcript)
    
    upload_to_drive(audio_path, AUDIO_FOLDER_ID)
    upload_to_drive(txt_path, TEXT_FOLDER_ID, content_type='text/plain')
    
    # Zoho Push
    zoho_id = await push_to_zoho(sub.transcript)
    if zoho_id:
        return {"status": "success", "msg": f"Lead created in Zoho! ID: {zoho_id}"}
    return {"status": "error", "msg": "Archives saved to Drive, but Zoho push failed."}

if __name__ == "__main__":
    import uvicorn
    # 🏎️ AUTO-RELOAD ENABLED FOR THE ARCHITECT
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
