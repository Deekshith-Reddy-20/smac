"""n8n workflow: Google Sheet calendar -> script -> visuals -> TTS -> video -> Drive."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "workflows" / "Loop-Work-Calendar-Drive.json"
ROOT_PATH = r"C:\Users\littu\OneDrive\Desktop\lit\loop-work"

SYSTEM_PROMPT = """You are the content director for LOOP WORK (n8n automation, website design, digital marketing). Faceless 9:16 Instagram Reel / YouTube Short.

LOOK: magic hour, golden rim light, teal shadows, photoreal, no text, no logos, no UI.

From the given calendar TOPIC only, write the script, then DIVIDE the script into exactly 6 scenes. Each scene has ONE visual type:

VISUAL MIX (exact):
- 2 scenes visual_type = "ai_image"
- 2 scenes visual_type = "stock_video"
- 1 scene visual_type = "stock_photo"
- 1 scene visual_type = "ai_video"

ai_prompt starts with: "cinematic still, magic hour, golden rim light, teal shadows,"
ai_video_prompt = same look + one camera move, 4 seconds, no text, no dialogue
stock_query = 3-6 real Pexels words, golden hour / laptop / small business. No brand names.
image_to_video_prompt = "slow cinematic push in, dust in sunbeams, no morphing, no text"

Hook in sentence 1. 125-155 words. Scene narrations concatenated = script.

Return JSON only:
{"title":"","hook":"","script":"","caption":"","hashtags":["loopwork"],"youtube_description":"","visual_plan":"2 ai_image + 2 stock_video + 1 stock_photo + 1 ai_video","scenes":[{"id":1,"narration":"","visual_type":"ai_image","stock_query":"","ai_prompt":"","ai_video_prompt":"","image_to_video_prompt":""}]}"""

CFG = "$('2. Config').first().json"
ROW = "$('3b. One topic').first().json"
PARSE = "$('5. Extract pack').first().json"
LOOP = "$('10. Loop scenes').item.json"
PAD = f"String({LOOP}.scene_no).padStart(2,'0')"
OUTDIR = f"{CFG}.outDir"
FOLDER = "$('8. Create Drive folder').first().json.id"


def node(name, ntype, params, pos, extra=None, tv=1):
    item = {
        "parameters": params,
        "id": name.lower().replace(" ", "-").replace(".", ""),
        "name": name,
        "type": ntype,
        "typeVersion": tv,
        "position": pos,
    }
    if extra:
        item.update(extra)
    return item


def sticky(name, text, pos, h=240, w=300, color=5):
    return node(
        name,
        "n8n-nodes-base.stickyNote",
        {"content": text, "height": h, "width": w, "color": color},
        pos,
    )


def sheets_creds():
    return {"googleSheetsOAuth2Api": {"id": "SHEETS", "name": "Google Sheets account"}}


def drive_creds():
    return {"googleDriveOAuth2Api": {"id": "DRIVE", "name": "Google Drive account"}}


def sheets_ids():
    return {
        "documentId": {
            "__rl": True,
            "value": f"={{ {CFG}.spreadsheetId }}",
            "mode": "id",
        },
        "sheetName": {
            "__rl": True,
            "value": f"={{ {CFG}.sheetName }}",
            "mode": "name",
        },
    }


def drive_parent():
    return {
        "driveId": {"__rl": True, "mode": "list", "value": "My Drive", "cachedResultName": "My Drive"},
        "folderId": {"__rl": True, "mode": "id", "value": f"={{ {FOLDER} }}"},
    }


def http_file(url_expr, timeout=120000):
    return {
        "url": url_expr,
        "options": {
            "timeout": timeout,
            "response": {"response": {"responseFormat": "file"}},
        },
    }


def switch_rule(key, value, cid):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [
                {
                    "id": cid,
                    "leftValue": "={{ $json.visual_type }}",
                    "rightValue": value,
                    "operator": {"type": "string", "operation": "equals"},
                }
            ],
            "combinator": "and",
        },
        "renameOutput": True,
        "outputKey": key,
    }


mkdir_cmd = (
    "={{ \"powershell -NoProfile -Command \\\"New-Item -ItemType Directory -Force -Path '\" + "
    f"{OUTDIR} + \"\\\\media','\" + {OUTDIR} + \"\\\\clips' | Out-Null\\\"\" }}"
)

ffmpeg_image = (
    "={{ \"ffmpeg -y -loop 1 -i \\\"\" + "
    f"{OUTDIR} + \"\\\\media\\\\scene_\" + {PAD} + \".jpg\\\" -t 7 -vf \\\"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30\\\" -an -c:v libx264 -pix_fmt yuv420p -preset veryfast \\\"\" + "
    f"{OUTDIR} + \"\\\\clips\\\\clip_\" + {PAD} + \".mp4\\\"\" }}"
)

ffmpeg_video = (
    "={{ \"ffmpeg -y -stream_loop -1 -i \\\"\" + "
    f"{OUTDIR} + \"\\\\media\\\\scene_\" + {PAD} + \".mp4\\\" -t 7 -vf \\\"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30\\\" -an -c:v libx264 -pix_fmt yuv420p -preset veryfast \\\"\" + "
    f"{OUTDIR} + \"\\\\clips\\\\clip_\" + {PAD} + \".mp4\\\"\" }}"
)

ffmpeg_final = (
    "={{ \"ffmpeg -y -f concat -safe 0 -i \\\"\" + "
    f"{OUTDIR} + \"\\\\clips\\\\concat.txt\\\" -i \\\"\" + "
    f"{OUTDIR} + \"\\\\voice.mp3\\\" -vf \\\"scale=1080:1920,format=yuv420p,drawtext=fontfile=C\\\\:/Windows/Fonts/arialbd.ttf:text=LOOP WORK:x=w-text_w-40:y=48:fontsize=32:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2\\\" -map 0:v:0 -map 1:a:0 -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k -shortest -movflags +faststart \\\"\" + "
    f"{OUTDIR} + \"\\\\loop-work-reel.mp4\\\"\" }}"
)

nodes = [
    sticky("STEP 1", "## 1. Sheet calendar\nEvery run takes the next row with status = pending.\nSchedule = 1 topic / day.\n\nPaste spreadsheet ID in Config.\nConnect Google Sheets login.", [-700, 80], color=5),
    node("1. Test in editor", "n8n-nodes-base.manualTrigger", {}, [-360, 120], tv=1),
    node(
        "1. Every morning",
        "n8n-nodes-base.scheduleTrigger",
        {"rule": {"interval": [{"field": "days", "triggerAtHour": 9, "triggerAtMinute": 0}]}},
        [-360, 320],
        tv=1.2,
    ),
    node(
        "2. Config",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "sid", "name": "spreadsheetId", "value": "PASTE_GOOGLE_SHEET_ID_HERE", "type": "string"},
                    {"id": "sn", "name": "sheetName", "value": "Calendar", "type": "string"},
                    {"id": "df", "name": "driveFolderId", "value": "PASTE_DRIVE_PARENT_FOLDER_ID_HERE", "type": "string"},
                    {"id": "rp", "name": "rootPath", "value": ROOT_PATH, "type": "string"},
                    {
                        "id": "out",
                        "name": "outDir",
                        "value": "={{ '" + ROOT_PATH.replace("\\", "\\\\") + "' + '\\\\output\\\\' + $now.toFormat('yyyyMMdd-HHmmss') }}",
                        "type": "string",
                    },
                    {"id": "gm", "name": "geminiModel", "value": "gemini-2.5-flash", "type": "string"},
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [0, 200],
        tv=3.4,
    ),
    node(
        "3. Read calendar",
        "n8n-nodes-base.googleSheets",
        {**sheets_ids(), "options": {}},
        [280, 200],
        extra={"credentials": sheets_creds()},
        tv=4.5,
    ),
    node(
        "3. Keep pending only",
        "n8n-nodes-base.filter",
        {
            "conditions": {
                "options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [
                    {
                        "id": "st",
                        "leftValue": "={{ $json.status }}",
                        "rightValue": "pending",
                        "operator": {"type": "string", "operation": "equals"},
                    }
                ],
                "combinator": "and",
            }
        },
        [540, 200],
        tv=2.2,
    ),
    node("3b. One topic", "n8n-nodes-base.limit", {"maxItems": 1}, [800, 200], tv=1),
    sticky("STEP 2", "## 2. Script from that topic\nGemini writes script AND divides scenes into:\nAI image / AI video / stock\nThen the Sheet is updated.", [0, -80], h=180, color=6),
    node(
        "4. Script prompt",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "sys", "name": "systemPrompt", "value": SYSTEM_PROMPT, "type": "string"},
                    {
                        "id": "usr",
                        "name": "userPrompt",
                        "value": f"={{ 'Channel: Loop Work. Platform: ' + {ROW}.platform + '\\nCalendar date: ' + {ROW}.date + '\\nTOPIC: ' + {ROW}.topic + '\\nDivide visuals from this topic only. Return JSON only.' }}",
                        "type": "string",
                    },
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [1060, 200],
        tv=3.4,
    ),
    node(
        "4. Gemini script + visual split",
        "n8n-nodes-base.httpRequest",
        {
            "method": "POST",
            "url": f"={{ 'https://generativelanguage.googleapis.com/v1beta/models/' + {CFG}.geminiModel + ':generateContent?key=' + $env.GEMINI_API_KEY }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ systemInstruction: { parts: [{ text: $json.systemPrompt }] }, contents: [{ role: 'user', parts: [{ text: $json.userPrompt }] }], generationConfig: { temperature: 0.75, responseMimeType: 'application/json' } }) }}",
            "options": {"timeout": 120000},
        },
        [1340, 200],
        tv=4.2,
    ),
    node(
        "5. Extract pack",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "pack",
                        "name": "pack",
                        "value": "={{ JSON.parse($json.candidates[0].content.parts[0].text.replaceAll('```json','').replaceAll('```','').trim()) }}",
                        "type": "object",
                    }
                ]
            },
            "options": {},
        },
        [1620, 200],
        tv=3.4,
    ),
    sticky("STEP 3", "## 3. Update Sheet + Drive folder\nScript lands in the row.\nOne Drive folder for this day holds script, images, stock, AI video, audio, final mp4.", [1900, -80], h=200, w=320, color=4),
    node(
        "6. Sheet: save script",
        "n8n-nodes-base.googleSheets",
        {
            **sheets_ids(),
            "operation": "update",
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "date": f"={{ {ROW}.date }}",
                    "status": "script_done",
                    "script": f"={{ {PARSE}.pack.script }}",
                    "hook": f"={{ {PARSE}.pack.hook }}",
                    "caption": f"={{ {PARSE}.pack.caption }}",
                    "hashtags": f"={{ ({PARSE}.pack.hashtags || []).join(' ') }}",
                    "visual_plan": f"={{ {PARSE}.pack.visual_plan }}",
                },
                "matchingColumns": ["date"],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        [1900, 200],
        extra={"credentials": sheets_creds()},
        tv=4.5,
    ),
    node(
        "7. Local folders",
        "n8n-nodes-base.executeCommand",
        {"command": mkdir_cmd},
        [2180, 80],
        tv=1,
    ),
    node(
        "8. Create Drive folder",
        "n8n-nodes-base.googleDrive",
        {
            "operation": "create",
            "name": f"={{ {ROW}.date + ' - ' + ({PARSE}.pack.title || {ROW}.topic) }}",
            "driveId": {"__rl": True, "mode": "list", "value": "My Drive", "cachedResultName": "My Drive"},
            "folderId": {"__rl": True, "mode": "id", "value": f"={{ {CFG}.driveFolderId }}"},
            "options": {},
        },
        [2180, 320],
        extra={"credentials": drive_creds()},
        tv=3,
    ),
    node(
        "8b. Script to file",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "t",
                        "name": "scriptText",
                        "value": f"={{ {PARSE}.pack.title + '\\n\\n' + {PARSE}.pack.script }}",
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        [2460, 320],
        tv=3.4,
    ),
    node(
        "8c. Script binary",
        "n8n-nodes-base.convertToFile",
        {"operation": "toText", "sourceProperty": "scriptText", "options": {"fileName": "script.txt", "encoding": "utf8"}},
        [2700, 320],
        tv=1.1,
    ),
    node(
        "8d. Upload script to Drive",
        "n8n-nodes-base.googleDrive",
        {"operation": "upload", "name": "script.txt", **drive_parent(), "options": {}},
        [2940, 320],
        extra={"credentials": drive_creds()},
        tv=3,
    ),
    node(
        "8e. Sheet: script Drive link",
        "n8n-nodes-base.googleSheets",
        {
            **sheets_ids(),
            "operation": "update",
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "date": f"={{ {ROW}.date }}",
                    "drive_folder": f"={{ 'https://drive.google.com/drive/folders/' + {FOLDER} }}",
                    "drive_script": "={{ $json.webViewLink || $json.webContentLink }}",
                },
                "matchingColumns": ["date"],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        [3180, 320],
        extra={"credentials": sheets_creds()},
        tv=4.5,
    ),
    sticky("STEP 4", "## 4. Visuals from the script split\nSwitch:\n• ai_image = Pollinations\n• stock_video / stock_photo = Pexels\n• ai_video = Pollinations wan-fast (free key) or fallback stock\nEach file -> Drive + local disk for FFmpeg.", [2460, 520], h=220, w=340, color=6),
    node(
        "9. Reload pack",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "pack", "name": "pack", "value": f"={{ {PARSE}.pack }}", "type": "object"}
                ]
            },
            "options": {},
        },
        [2460, 720],
        tv=3.4,
    ),
    node("9b. Split scenes", "n8n-nodes-base.splitOut", {"fieldToSplitOut": "pack.scenes", "options": {}}, [2700, 720], tv=1),
    node(
        "9c. Number scenes",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "no", "name": "scene_no", "value": "={{ $itemIndex + 1 }}", "type": "number"}
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [2940, 720],
        tv=3.4,
    ),
    node("10. Loop scenes", "n8n-nodes-base.splitInBatches", {"options": {}}, [3180, 720], tv=3),
    node(
        "11. Switch visual type",
        "n8n-nodes-base.switch",
        {
            "rules": {
                "values": [
                    switch_rule("ai_image", "ai_image", "v1"),
                    switch_rule("stock_video", "stock_video", "v2"),
                    switch_rule("stock_photo", "stock_photo", "v3"),
                    switch_rule("ai_video", "ai_video", "v4"),
                ]
            },
            "options": {"fallbackOutput": "extra"},
        },
        [3460, 720],
        tv=3.2,
    ),
    node(
        "12. AI image",
        "n8n-nodes-base.httpRequest",
        http_file(
            f"={{ 'https://image.pollinations.ai/prompt/' + encodeURIComponent(({LOOP}.ai_prompt || 'cinematic still, magic hour, golden rim light, teal shadows, photoreal workspace') ) + '?width=1080&height=1920&model=flux&nologo=true' }}",
            180000,
        ),
        [3800, 200],
        tv=4.2,
    ),
    node(
        "13. Pexels video search",
        "n8n-nodes-base.httpRequest",
        {
            "url": f"={{ 'https://api.pexels.com/v1/videos/search?query=' + encodeURIComponent({LOOP}.stock_query || 'golden hour laptop') + '&orientation=portrait&per_page=5' }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $env.PEXELS_API_KEY }}"}]},
            "options": {"timeout": 60000},
        },
        [3800, 480],
        tv=4.2,
    ),
    node(
        "13b. Pick video URL",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "u", "name": "mediaUrl", "value": "={{ $json.videos[0].video_files[0].link }}", "type": "string"}
                ]
            },
            "options": {},
        },
        [4080, 480],
        tv=3.4,
    ),
    node("13c. Download stock video", "n8n-nodes-base.httpRequest", http_file("={{ $json.mediaUrl }}"), [4360, 480], tv=4.2),
    node(
        "14. Pexels photo search",
        "n8n-nodes-base.httpRequest",
        {
            "url": f"={{ 'https://api.pexels.com/v1/search?query=' + encodeURIComponent({LOOP}.stock_query || 'golden hour office') + '&orientation=portrait&per_page=5' }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $env.PEXELS_API_KEY }}"}]},
            "options": {"timeout": 60000},
        },
        [3800, 720],
        tv=4.2,
    ),
    node(
        "14b. Pick photo URL",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "u",
                        "name": "mediaUrl",
                        "value": "={{ $json.photos[0].src.portrait || $json.photos[0].src.large }}",
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        [4080, 720],
        tv=3.4,
    ),
    node("14c. Download stock photo", "n8n-nodes-base.httpRequest", http_file("={{ $json.mediaUrl }}", 90000), [4360, 720], tv=4.2),
    node(
        "15. AI video (wan-fast)",
        "n8n-nodes-base.httpRequest",
        http_file(
            f"={{ 'https://gen.pollinations.ai/video/' + encodeURIComponent({LOOP}.ai_video_prompt || {LOOP}.ai_prompt || 'magic hour cinematic office, slow push in') + '?model=wan-fast&duration=4&aspectRatio=9:16&key=' + $env.POLLINATIONS_KEY }}",
            240000,
        ),
        [3800, 980],
        extra={"onError": "continueErrorOutput"},
        tv=4.2,
    ),
    node(
        "16. Save visual disk",
        "n8n-nodes-base.writeBinaryFile",
        {
            "fileName": (
                "={{ "
                f"{OUTDIR} + \"\\\\media\\\\scene_\" + {PAD} + \".\" + "
                f"(['stock_video','ai_video'].includes({LOOP}.visual_type) ? 'mp4' : 'jpg') }}"
            ),
            "options": {},
        },
        [4680, 600],
        tv=1,
    ),
    node(
        "16r. Read visual",
        "n8n-nodes-base.readWriteFile",
        {
            "operation": "read",
            "fileSelector": (
                "={{ "
                f"{OUTDIR} + \"\\\\media\\\\scene_\" + {PAD} + \".\" + "
                f"(['stock_video','ai_video'].includes({LOOP}.visual_type) ? 'mp4' : 'jpg') }}"
            ),
            "options": {},
        },
        [4820, 600],
        tv=1,
    ),
    node(
        "16b. Upload visual Drive",
        "n8n-nodes-base.googleDrive",
        {
            "operation": "upload",
            "name": (
                "={{ 'scene_' + "
                f"{PAD}"
                + " + '_' + "
                f"{LOOP}.visual_type"
                + " + '.' + (['stock_video','ai_video'].includes("
                f"{LOOP}.visual_type) ? 'mp4' : 'jpg') }}"
            ),
            **drive_parent(),
            "options": {},
        },
        [4960, 600],
        extra={"credentials": drive_creds()},
        tv=3,
    ),
    node(
        "17. Image clip?",
        "n8n-nodes-base.if",
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [
                    {
                        "id": "im",
                        "leftValue": f"={{ ['ai_image','stock_photo'].includes({LOOP}.visual_type) }}",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }
                ],
                "combinator": "and",
            }
        },
        [5240, 600],
        tv=2.2,
    ),
    node("17a. FFmpeg image", "n8n-nodes-base.executeCommand", {"command": ffmpeg_image}, [5520, 460], tv=1),
    node("17b. FFmpeg video", "n8n-nodes-base.executeCommand", {"command": ffmpeg_video}, [5520, 740], tv=1),
    node(
        "17c. Wait 8 sec",
        "n8n-nodes-base.wait",
        {"resume": "timeInterval", "amount": 8, "unit": "seconds"},
        [5800, 600],
        tv=1.1,
    ),
    sticky("STEP 5-7", "## 5 TTS  ## 6 Combine  ## 7 Drive + Sheet\nVoice -> Drive\nFFmpeg final mp4\nUpload audio + video\nSheet status = ready", [3180, 1080], h=200, color=7),
    node(
        "18. Generate voice",
        "n8n-nodes-base.httpRequest",
        http_file(
            f"={{ 'https://text.pollinations.ai/' + encodeURIComponent({PARSE}.pack.script) + '?model=openai-audio&voice=nova' }}",
            180000,
        ),
        [3460, 1200],
        tv=4.2,
    ),
    node(
        "18b. Save voice disk",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": f"={{ {OUTDIR} + '\\\\voice.mp3' }}", "options": {}},
        [3740, 1200],
        tv=1,
    ),
    node(
        "18r. Read voice",
        "n8n-nodes-base.readWriteFile",
        {"operation": "read", "fileSelector": f"={{ {OUTDIR} + '\\\\voice.mp3' }}", "options": {}},
        [3880, 1200],
        tv=1,
    ),
    node(
        "18c. Upload audio Drive",
        "n8n-nodes-base.googleDrive",
        {"operation": "upload", "name": "voice.mp3", **drive_parent(), "options": {}},
        [4020, 1200],
        extra={"credentials": drive_creds()},
        tv=3,
    ),
    node(
        "19. Concat list",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "c",
                        "name": "concatList",
                        "value": (
                            "={{ ['01','02','03','04','05','06'].map(n => \"file '\" + "
                            f"{OUTDIR}.replaceAll('\\\\','/') + '/clips/clip_' + n + \".mp4'\").join('\\n') }}"
                        ),
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        [4300, 1200],
        tv=3.4,
    ),
    node(
        "19b. Concat file",
        "n8n-nodes-base.convertToFile",
        {"operation": "toText", "sourceProperty": "concatList", "options": {"fileName": "concat.txt", "encoding": "utf8"}},
        [4580, 1200],
        tv=1.1,
    ),
    node(
        "19c. Save concat",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": f"={{ {OUTDIR} + '\\\\clips\\\\concat.txt' }}", "options": {}},
        [4860, 1200],
        tv=1,
    ),
    node("20. Render final video", "n8n-nodes-base.executeCommand", {"command": ffmpeg_final}, [5140, 1200], tv=1),
    node(
        "20b. Read final mp4",
        "n8n-nodes-base.readWriteFile",
        {"operation": "read", "fileSelector": f"={{ {OUTDIR} + '\\\\loop-work-reel.mp4' }}", "options": {}},
        [5420, 1200],
        tv=1,
    ),
    node(
        "20c. Upload final Drive",
        "n8n-nodes-base.googleDrive",
        {"operation": "upload", "name": "loop-work-reel.mp4", **drive_parent(), "options": {}},
        [5700, 1200],
        extra={"credentials": drive_creds()},
        tv=3,
    ),
    node(
        "21. Sheet: ready + links",
        "n8n-nodes-base.googleSheets",
        {
            **sheets_ids(),
            "operation": "update",
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "date": f"={{ {ROW}.date }}",
                    "status": "ready",
                    "drive_audio": "={{ $('18c. Upload audio Drive').first().json.webViewLink }}",
                    "drive_final": "={{ $json.webViewLink || $json.webContentLink }}",
                    "drive_images": f"={{ 'https://drive.google.com/drive/folders/' + {FOLDER} }}",
                    "drive_stock": f"={{ 'https://drive.google.com/drive/folders/' + {FOLDER} }}",
                    "drive_ai_video": f"={{ 'https://drive.google.com/drive/folders/' + {FOLDER} }}",
                    "notes": "All files are in the Drive folder for this day",
                },
                "matchingColumns": ["date"],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        [5980, 1200],
        extra={"credentials": sheets_creds()},
        tv=4.5,
    ),
]

connections = {
    "1. Test in editor": {"main": [[{"node": "2. Config", "type": "main", "index": 0}]]},
    "1. Every morning": {"main": [[{"node": "2. Config", "type": "main", "index": 0}]]},
    "2. Config": {"main": [[{"node": "3. Read calendar", "type": "main", "index": 0}]]},
    "3. Read calendar": {"main": [[{"node": "3. Keep pending only", "type": "main", "index": 0}]]},
    "3. Keep pending only": {"main": [[{"node": "3b. One topic", "type": "main", "index": 0}]]},
    "3b. One topic": {"main": [[{"node": "4. Script prompt", "type": "main", "index": 0}]]},
    "4. Script prompt": {"main": [[{"node": "4. Gemini script + visual split", "type": "main", "index": 0}]]},
    "4. Gemini script + visual split": {"main": [[{"node": "5. Extract pack", "type": "main", "index": 0}]]},
    "5. Extract pack": {"main": [[{"node": "6. Sheet: save script", "type": "main", "index": 0}]]},
    "6. Sheet: save script": {
        "main": [
            [
                {"node": "7. Local folders", "type": "main", "index": 0},
                {"node": "8. Create Drive folder", "type": "main", "index": 0},
            ]
        ]
    },
    "8. Create Drive folder": {"main": [[{"node": "8b. Script to file", "type": "main", "index": 0}]]},
    "8b. Script to file": {"main": [[{"node": "8c. Script binary", "type": "main", "index": 0}]]},
    "8c. Script binary": {"main": [[{"node": "8d. Upload script to Drive", "type": "main", "index": 0}]]},
    "8d. Upload script to Drive": {"main": [[{"node": "8e. Sheet: script Drive link", "type": "main", "index": 0}]]},
    "8e. Sheet: script Drive link": {"main": [[{"node": "9. Reload pack", "type": "main", "index": 0}]]},
    "7. Local folders": {"main": [[{"node": "9. Reload pack", "type": "main", "index": 0}]]},
    "9. Reload pack": {"main": [[{"node": "9b. Split scenes", "type": "main", "index": 0}]]},
    "9b. Split scenes": {"main": [[{"node": "9c. Number scenes", "type": "main", "index": 0}]]},
    "9c. Number scenes": {"main": [[{"node": "10. Loop scenes", "type": "main", "index": 0}]]},
    "10. Loop scenes": {
        "main": [
            [{"node": "18. Generate voice", "type": "main", "index": 0}],
            [{"node": "11. Switch visual type", "type": "main", "index": 0}],
        ]
    },
    "11. Switch visual type": {
        "main": [
            [{"node": "12. AI image", "type": "main", "index": 0}],
            [{"node": "13. Pexels video search", "type": "main", "index": 0}],
            [{"node": "14. Pexels photo search", "type": "main", "index": 0}],
            [{"node": "15. AI video (wan-fast)", "type": "main", "index": 0}],
            [{"node": "13. Pexels video search", "type": "main", "index": 0}],
        ]
    },
    "12. AI image": {"main": [[{"node": "16. Save visual disk", "type": "main", "index": 0}]]},
    "13. Pexels video search": {"main": [[{"node": "13b. Pick video URL", "type": "main", "index": 0}]]},
    "13b. Pick video URL": {"main": [[{"node": "13c. Download stock video", "type": "main", "index": 0}]]},
    "13c. Download stock video": {"main": [[{"node": "16. Save visual disk", "type": "main", "index": 0}]]},
    "14. Pexels photo search": {"main": [[{"node": "14b. Pick photo URL", "type": "main", "index": 0}]]},
    "14b. Pick photo URL": {"main": [[{"node": "14c. Download stock photo", "type": "main", "index": 0}]]},
    "14c. Download stock photo": {"main": [[{"node": "16. Save visual disk", "type": "main", "index": 0}]]},
    "15. AI video (wan-fast)": {
        "main": [
            [{"node": "16. Save visual disk", "type": "main", "index": 0}],
            [{"node": "13. Pexels video search", "type": "main", "index": 0}],
        ]
    },
    "16. Save visual disk": {"main": [[{"node": "16r. Read visual", "type": "main", "index": 0}]]},
    "16r. Read visual": {"main": [[{"node": "16b. Upload visual Drive", "type": "main", "index": 0}]]},
    "16b. Upload visual Drive": {"main": [[{"node": "17. Image clip?", "type": "main", "index": 0}]]},
    "17. Image clip?": {
        "main": [
            [{"node": "17a. FFmpeg image", "type": "main", "index": 0}],
            [{"node": "17b. FFmpeg video", "type": "main", "index": 0}],
        ]
    },
    "17a. FFmpeg image": {"main": [[{"node": "17c. Wait 8 sec", "type": "main", "index": 0}]]},
    "17b. FFmpeg video": {"main": [[{"node": "17c. Wait 8 sec", "type": "main", "index": 0}]]},
    "17c. Wait 8 sec": {"main": [[{"node": "10. Loop scenes", "type": "main", "index": 0}]]},
    "18. Generate voice": {"main": [[{"node": "18b. Save voice disk", "type": "main", "index": 0}]]},
    "18b. Save voice disk": {"main": [[{"node": "18r. Read voice", "type": "main", "index": 0}]]},
    "18r. Read voice": {"main": [[{"node": "18c. Upload audio Drive", "type": "main", "index": 0}]]},
    "18c. Upload audio Drive": {"main": [[{"node": "19. Concat list", "type": "main", "index": 0}]]},
    "19. Concat list": {"main": [[{"node": "19b. Concat file", "type": "main", "index": 0}]]},
    "19b. Concat file": {"main": [[{"node": "19c. Save concat", "type": "main", "index": 0}]]},
    "19c. Save concat": {"main": [[{"node": "20. Render final video", "type": "main", "index": 0}]]},
    "20. Render final video": {"main": [[{"node": "20b. Read final mp4", "type": "main", "index": 0}]]},
    "20b. Read final mp4": {"main": [[{"node": "20c. Upload final Drive", "type": "main", "index": 0}]]},
    "20c. Upload final Drive": {"main": [[{"node": "21. Sheet: ready + links", "type": "main", "index": 0}]]},
}

# Merge local folders + drive folder before reload: both connect to Reload pack.
# splitInBatches / Merge issue: 7. Local folders and 8e both go to Reload — race.
# Fix: 7. Local folders should wait until Drive script is uploaded.
# Connect 6 only to 8 Create Drive, and Create Drive also needs local folders first.
# Better: 6 -> 7 Local folders -> 8 Create Drive -> ... -> 9 Reload
# Remove parallel from 6.

connections["6. Sheet: save script"] = {"main": [[{"node": "7. Local folders", "type": "main", "index": 0}]]}
connections["7. Local folders"] = {"main": [[{"node": "8. Create Drive folder", "type": "main", "index": 0}]]}

workflow = {
    "name": "Loop Work — Calendar Sheet + Drive",
    "nodes": nodes,
    "connections": connections,
    "active": False,
    "settings": {"executionOrder": "v1"},
    "versionId": "loop-work-calendar-drive-v1",
    "meta": {"templateCredsSetupCompleted": False},
    "id": "loopWorkCalendarDrive",
    "tags": [],
}

for i, n in enumerate(workflow["nodes"]):
    n["id"] = f"cd{i:03d}"

OUT.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
print(f"Wrote {OUT} ({len(nodes)} nodes)")
