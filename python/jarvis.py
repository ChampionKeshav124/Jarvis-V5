"""
═══════════════════════════════════════════════════════════════
 JARVIS V5.5 — Python Backend Bridge
 BYTEFORGE SYSTEM

 V5.5: Local Intent Engine — System commands handled INSTANTLY,
       no API required. Gemini used for complex conversation only.
═══════════════════════════════════════════════════════════════
"""

import sys
import json
import os
import base64
import requests
import re

# ── API Keys & Config ─────────────────────────────────────────
def _load_config(key_name, default_val):
    try:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        sys.path.insert(0, parent_dir)
        import config
        return getattr(config, key_name, default_val)
    except Exception:
        return os.environ.get(key_name, default_val)

GEMINI_API_KEY    = _load_config("GEMINI_API_KEY",    "YOUR_API_KEY")
ELEVENLABS_API_KEY  = _load_config("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = _load_config("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJcg")

# ── System Control Integration ───────────────────────────────
try:
    from system_tools import tools
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from system_tools import tools

# ── Local Intent Patterns (no API needed) ────────────────────
# These patterns are matched INSTANTLY without any network call.
_OPEN_APP_PATTERN  = re.compile(
    r'^(?:please\s+)?(?:open|launch|start|run|execute|play)\s+(?:the\s+)?(.+?)(?:\s+(?:app|application|program|software))?\s*$',
    re.IGNORECASE
)
_CLOSE_APP_PATTERN = re.compile(
    r'^(?:please\s+)?(?:close|quit|kill|terminate|exit|stop)\s+(?:the\s+)?(.+?)(?:\s+(?:app|application|program|software))?\s*$',
    re.IGNORECASE
)
_OPEN_URL_PATTERN  = re.compile(
    r'^(?:please\s+)?(?:open|go\s+to|navigate\s+to|visit|browse\s+to|show\s+me)\s+(?:the\s+)?(?:website\s+)?(?:https?://)?(.+?)\s*$',
    re.IGNORECASE
)
_SEARCH_SYSTEM_PATTERN = re.compile(
    r'^(?:please\s+)?search\s+(?:the|my)?\s*(?:system|computer|pc|files)\s+(?:for\s+)?(.+?)\s*$',
    re.IGNORECASE
)
_SEARCH_GOOGLE_PATTERN = re.compile(
    r'^(?:please\s+)?(?:search\s+(?:in\s+)?google|google)\s+(?:for\s?|the\s?)?(.+?)(?:\s+online|\s+on\s+the\s+web)?\s*$',
    re.IGNORECASE
)
_IDLE_MODE_PATTERN = re.compile(
    r'^(?:please\s+)?(?:enter|go\s+to|put\s+in|switch\s+to)\s+(?:idle|sleep|quiet|waiting)\s+mode\s*$',
    re.IGNORECASE
)

# --- TITAN PATTERNS ---
_GAME_INSTALL_PATTERN = re.compile(
    r'^(?:please\s+)?(?:ins.*?|setup|get|download|play)\s+(.+?)(?:\s+(?:on|from|in)\s+(steam|epic|epic\s+games))?\s*$',
    re.IGNORECASE
)
_WHATSAPP_PATTERN = re.compile(
    r'^(?:please\s+)?(?:send\s+(?:a\s+)?whatsapp|whatsapp)\s+(?:to\s+)?(\d+)\s+(?:saying|message|texting)\s+(.+?)\s*$',
    re.IGNORECASE
)
_SCOUT_PATTERN = re.compile(
    r'^(?:please\s+)?(?:search|scout|look\s+up)\s+(amazon|github|reddit|youtube)\s+(?:for\s+)?(.+?)\s*$',
    re.IGNORECASE
)
_TYPE_PATTERN = re.compile(
    r'^(?:please\s+)?(?:type|write|dictate)\s+(.+?)\s*$',
    re.IGNORECASE
)
_YOUTUBE_PATTERN = re.compile(
    r'^(?:please\s+)?(?:play|find)\s+(.+?)\s+on\s+youtube\s*$',
    re.IGNORECASE
)
_UPDATE_PATTERN = re.compile(
    r'^(?:please\s+)?(?:update|upgrade)\s+(?:my\s+)?(?:pc|computer|system|software|games)(?:\s+now)?\s*$',
    re.IGNORECASE
)
# Vision-Atomic Patterns (Titan-Vision Upgrade)
_CLICK_PATTERN  = re.compile(r"(?i)^(?:please\s+)?(?:click|tap|double click|right click)\s*(?:on|at)?\s*(.*)$")
_FIND_PATTERN   = re.compile(r"(?i)^(?:please\s+)?(?:find|locate|where is)\s+(.*)$")
_SCROLL_PATTERN = re.compile(r"(?i)^(?:please\s+)?scroll\s+(up|down|left|right)?(?:\s+(.*))?$")
_HOTKEY_PATTERN = re.compile(r"(?i)^(?:please\s+)?(?:press|hotkey)\s+(.*)$")
# ----------------------

_SEARCH_PATTERN = re.compile(
    r'^(?:please\s+)?(?:search|find|look\s+for|locate)\s+(?:for\s+)?(.+?)\s*$',
    re.IGNORECASE
)

# Popular AppID Mapping for Zero-Lag (Steam)
_COMMON_STEAM_IDS = {
    "csgo": "730", "counter strike": "730", "cs2": "730",
    "dota": "570", "dota 2": "570",
    "pubg": "578080", "elden ring": "1245620",
    "cyberpunk": "1091500", "gta": "271590", "stardew valley": "413150"
}
# JARVIS STATE (Context for Aegis Protocol)
def load_state():
    try:
        with open(os.path.join(os.path.dirname(__file__), "state.json"), "r") as f:
            return json.load(f)
    except Exception:
        return {"last_scout": None}

def save_state(state):
    try:
        with open(os.path.join(os.path.dirname(__file__), "state.json"), "w") as f:
            json.dump(state, f)
    except Exception:
        pass

_JARVIS_STATE = load_state()

def _local_intent(command: str):
    """
    Tries to match command against local patterns instantly.
    Returns (action_fn, arg) or None if no match.
    """
    cmd = command.strip().lower()

    # 1. Aegis Confirmation (Yes/Proceed/Go for it)
    confirm_words = ["yes", "yep", "yey", "yeah", "do it", "proceed", "go for it", "install", "sure", "ok"]
    if any(word in cmd for word in confirm_words) and len(cmd.split()) <= 4:
        scout = _JARVIS_STATE.get("last_scout")
        if scout:
            if scout["source"] == "steam":
                # Trigger Small Mode Install Protocol
                _JARVIS_STATE["last_scout"] = None
                save_state(_JARVIS_STATE)
                return (lambda x: tools.steam_action("install", app_id=scout.get("id"), game_name=scout["name"]), None)
            else:
                _JARVIS_STATE["last_scout"] = None
                save_state(_JARVIS_STATE)
                return (lambda x: tools.epic_action("search", scout["name"]), None)

    # 2. Gaming (Aegis Scout Logic)
    m = _GAME_INSTALL_PATTERN.match(cmd)
    if m:
        return _scout_game(m.group(1).strip().lower())

    # 3. Messaging (WhatsApp)
    m = _WHATSAPP_PATTERN.match(cmd)
    if m:
        phone, msg = m.group(1), m.group(2)
        return (lambda x: tools.send_whatsapp(phone, msg), None)

    # 3. Web Scout
    m = _SCOUT_PATTERN.match(cmd)
    if m:
        platform, query = m.group(1), m.group(2)
        return (lambda x: tools.web_scout(platform, query), None)

    # 3.1 YouTube Play
    m = _YOUTUBE_PATTERN.match(cmd)
    if m:
        return (lambda x: tools.play_youtube(m.group(1).strip()), None)

    # 3.2 Typing Dictation (Now with Smart-Type)
    m = _TYPE_PATTERN.match(cmd)
    if m:
        text = m.group(1).strip()
        return (lambda x: tools.computer_action({"action": "smart_type", "text": text}), None)
        
    # 3.3 System Update
    if _UPDATE_PATTERN.match(cmd):
        return (lambda x: tools.update_system(), None)

    # 3.4 Vision & Atomic Control (Titan-Vision)
    m = _CLICK_PATTERN.match(cmd)
    if m:
        target = m.group(1).strip()
        if not target: # Just a generic click
            return (lambda x: tools.computer_action({"action": "click"}), None)
        # AI-Powered Click on Description
        return (lambda x: tools.computer_action({"action": "screen_click", "description": target}), None)

    m = _FIND_PATTERN.match(cmd)
    if m:
        target = m.group(1).strip()
        return (lambda x: tools.computer_action({"action": "screen_find", "description": target}), None)

    m = _SCROLL_PATTERN.match(cmd)
    if m:
        direction = m.group(1) or "down"
        amount = 3
        try: # Try to catch numeric amount if user said "scroll down 5"
            parts = (m.group(2) or "").split()
            if parts and parts[0].isdigit(): amount = int(parts[0])
        except: pass
        return (lambda x: tools.computer_action({"action": "scroll", "direction": direction, "amount": amount}), None)

    m = _HOTKEY_PATTERN.match(cmd)
    if m:
        return (lambda x: tools.computer_action({"action": "hotkey", "keys": m.group(1).strip()}), None)

    # 4. Search Google
    m = _SEARCH_GOOGLE_PATTERN.match(cmd)
    if m:
        return (tools.search_google, m.group(1).strip())

    # 5. Search System Files
    m = _SEARCH_SYSTEM_PATTERN.match(cmd)
    if m:
        return (tools.search_files, m.group(1).strip())

    # 6. Idle Mode
    if _IDLE_MODE_PATTERN.match(cmd):
        return (lambda x: "Entering idle mode. I'll be here if you need me.", None)

    # 7. Open App or Website
    m = _OPEN_APP_PATTERN.match(cmd)
    if m:
        target = m.group(1).strip().lower()
        url_keywords = ["youtube", "google", "github", "reddit", "twitter", "instagram", "facebook", "netflix", "amazon", "udemy", "stackoverflow", "linkedin"]
        if "." in target or target in url_keywords:
            return (tools.open_url, target)
        return (tools.open_application, target)

    # 4. Close App
    m = _CLOSE_APP_PATTERN.match(cmd)
    if m:
        return (tools.close_application, m.group(1).strip())

    # 5. Explicit URL Open
    m = _OPEN_URL_PATTERN.match(cmd)
    if m:
        target = m.group(1).strip()
        url_keywords = ["youtube", "google", "github", "reddit", "twitter", "instagram", "facebook", "netflix", "amazon", "udemy", "stackoverflow", "linkedin"]
        if "." in target or target.lower() in url_keywords:
            return (tools.open_url, target)

    # 6. Generic Search (Default to Files)
    m = _SEARCH_PATTERN.match(cmd)
    if m:
        return (tools.search_files, m.group(1).strip())

    # 7. FUZZY FALLBACK: Catch 'install' anywhere if regex failed
    if "ins" in cmd or "get" in cmd or "download" in cmd:
        # Try to extract potential game name (everything after the keyword)
        words = cmd.split()
        for i, word in enumerate(words):
            if any(k in word for k in ["ins", "get", "down"]):
                potential_name = " ".join(words[i+1:])
                if potential_name:
                    return _scout_game(potential_name)

    return None


def _split_commands(command: str) -> list:
    """Splits a multi-part command by common delimiters, avoiding splitting quoted text."""
    # Split by: " and ", " then ", or "," (basic regex)
    # We use negative lookahead to avoid splitting inside quotes if possible
    parts = re.split(r'\s+and\s+|\s+then\s+|\s*,\s*', command, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]

def get_gemini_response(user_input: str) -> dict:
    """Sends complex/conversational input to Gemini."""
    import time
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=GEMINI_API_KEY)

        SYSTEM_PROMPT = (
            "You are JARVIS V5.6, a highly advanced AI core by BYTEFORGE SYSTEM. "
            "Keep responses short, confident, calm, and slightly formal. "
            "Do not use markdown. Use clean, natural sentences. "
            "BE EXTREMELY TOLERANT OF TYPOS. If the user says 'insrall', assume they meant 'install'. "
            "Your functions include software and game installation via the 'open_application' or specialized Steam triggers."
        )

        tool_schema = [
            {"name": "open_application",  "description": "Opens a computer application by name.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}},
            {"name": "close_application", "description": "Closes a running application by name.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}},
            {"name": "open_url",          "description": "Opens a URL in the browser.",            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
            {"name": "search_files",      "description": "Searches for files by name/keyword.",    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        ]

        cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=tool_schema)],
            temperature=0.7
        )

        MODEL = "gemini-2.5-flash"
        response = None
        for attempt in range(2):
            try:
                response = client.models.generate_content(model=MODEL, contents=user_input, config=cfg)
                break
            except Exception:
                if attempt == 0: MODEL = "gemini-2.0-flash"
                else: raise

        final_text = ""
        action_performed = None

        if response and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fn_name  = part.function_call.name
                    fn_args  = part.function_call.args
                    action_performed = f"execute:{fn_name}"
                    if hasattr(tools, fn_name):
                        tool_result  = getattr(tools, fn_name)(**fn_args)
                        final_text = _local_personality(fn_name, fn_args, tool_result)
                    else:
                        final_text = f"I cannot access the {fn_name} protocol."
                elif part.text:
                    final_text += part.text

        return {"response": final_text.strip() or "Process complete.", "action": action_performed}
    except Exception as e:
        return {"response": f"AI core error: {e}", "action": "error"}

def _local_personality(fn_name: str, fn_args: dict, result: str) -> str:
    """Generates a short, human-like response for actions."""
    if fn_name == "open_application":
        return f"Launching {fn_args.get('app_name', 'application')}."
    if fn_name == "close_application":
        return f"Terminating {fn_args.get('app_name', 'process')}."
    if fn_name == "open_url":
        return f"Opening {fn_args.get('url', 'link')}."
    return result

def get_elevenlabs_audio_base64(text: str) -> str:
    """Returns base64 audio or None."""
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY in ("", "YOUR_ELEVEN_KEY"): return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    try:
        r = requests.post(url, json={"text": text, "model_id": "eleven_multilingual_v2"}, 
                          headers={"xi-api-key": ELEVENLABS_API_KEY}, timeout=10)
        if r.status_code == 200: return base64.b64encode(r.content).decode("utf-8")
    except: pass
    return None

def process_command(command: str, use_voice: bool = False) -> dict:
    """Main command processor supporting multi-command sequences."""
    lower = command.lower().strip()
    if command == "__system_startup__":
        res = "JARVIS V5.7 online. Standing by."
        return {"response": res, "action": None, "audio_base64": get_elevenlabs_audio_base64(res) if use_voice else None}

    if lower in ("exit", "quit", "shutdown"):
        return {"response": "Shutting down.", "action": "exit"}

    # Split command into parts: "Open Youtube and Spotify" -> ["Open Youtube", "Spotify"]
    sub_commands = _split_commands(command)
    all_responses = []
    final_action = None

    for sub in sub_commands:
        # 1. Try Local Intent Engine
        intent = _local_intent(sub)
        if intent:
            fn, arg = intent
            res_text = fn(arg)
            # Map simple result back to personality
            all_responses.append(res_text)
            final_action = "execute:multi"
            continue

        # 2. Fallback to Gemini for complex/conversational parts
        ai_res = get_gemini_response(sub)
        all_responses.append(ai_res.get("response", ""))
        if ai_res.get("action"): final_action = ai_res["action"]

    # Combine all responses into one clean sentence
    full_response = " ".join(all_responses).strip()
    if not full_response: full_response = "Command processed."

    return {
        "response": full_response,
        "action": final_action,
        "audio_base64": get_elevenlabs_audio_base64(full_response) if use_voice else None
    }

def _scout_game(game_name):
    """Internal Aegis Scout Protocol for searching and verifying games."""
    # Look for Steam ID locally first
    appid = None
    for key, val in _COMMON_STEAM_IDS.items():
        if key in game_name or game_name in key:
            appid = val
            break
    if not appid:
        appid = tools.search_steam_api(game_name)
    
    if appid:
        details = tools.get_steam_details(appid)
        if details:
            # 1. Zero-Touch Protocol (If Free, just do it)
            if details["is_free"]:
                msg = f"I found '{details['name']}' on Steam and it's Free to Play. I am starting the installation wizard for you right now."
                return (lambda x: tools.steam_action("install", app_id=appid, game_name=details["name"]), msg)
            
            # 2. Paid Protocol (Ask for Aegis permission)
            _JARVIS_STATE["last_scout"] = {"name": details["name"], "id": appid, "source": "steam", "price": details["price"]}
            save_state(_JARVIS_STATE)
            price_info = details["price"]
            msg = f"I found '{details['name']}' on Steam for {price_info}. Since it's a paid game, I'll wait for your permission. Shall I proceed with the installation protocol?"
            return (lambda x: msg, None)

    # completely unknown or Epic exclusive
    _JARVIS_STATE["last_scout"] = {"name": game_name, "source": "epic"}
    save_state(_JARVIS_STATE)
    msg = f"I couldn't find '{game_name}' on Steam. I'll search Epic Games Store for it."
    return (lambda x: tools.epic_action("search", game_name), None)

if __name__ == "__main__":
    # Force UTF-8 for Windows output compatibility with emojis
    if sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Silencing stray prints from libraries until the final result is ready
    actual_stdout = sys.stdout
    sys.stdout = sys.stderr

    try:
        args = sys.argv[1:]
        use_voice = "--voice" in args
        if use_voice: args.remove("--voice")
        
        user_cmd = " ".join(args) if args else ""
        if not user_cmd:
            result = {"response": "No command.", "action": None}
        else:
            result = process_command(user_cmd, use_voice=use_voice)

        # Restore stdout and print the final JSON result
        sys.stdout = actual_stdout
        print(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()
    except Exception as fatal_err:
        sys.stdout = actual_stdout
        print(json.dumps({"response": f"Backend fatal error: {fatal_err}", "action": "error"}))
