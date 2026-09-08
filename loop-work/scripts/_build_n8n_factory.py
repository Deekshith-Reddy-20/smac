"""Build the visual n8n Content Factory workflow (nodes only, no Python engine)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "workflows" / "Loop-Work-Content-Factory.json"
ROOT_PATH = r"C:\Users\littu\OneDrive\Desktop\lit\loop-work"

SYSTEM_PROMPT = """You are the content director and cinematographer for LOOP WORK.

LOOP WORK sells: n8n automation, website design, digital marketing.
Audience: small business owners. Faceless 9:16 Reel / YouTube Short only.

LOOK LOCK (every AI still and AI clip must match):
- Magic hour / golden hour only: warm sun, long shadows, amber rim light, teal shadows, cinematic haze
- Photoreal, 35mm, shallow depth of field, anamorphic bokeh, premium tech brand
- Dark teal + gold grade. No noon sun. No office fluorescent. No cartoon. No 3D render look
- NEVER any readable text, UI, logos, watermarks, subtitles, captions, hands holding phones with screens of text

VOICE:
- Hook in sentence 1. No "Hey guys", no "in this video", no guru hype
- Specific tools and numbers. 125-155 spoken words
- Exactly 6 scenes. Concatenated scene narration MUST equal script

VISUAL MIX (exact, do not change counts):
1 pexels_video = hook energy, real stock motion
2 ai_image = custom magic-hour stills (your look)
1 pexels_photo = real stock still
1 local = creator file, local_hint only
1 ai_video = ONE short 4-5s motion clip, same magic-hour look

pexels_query = 3-6 real B-roll words. Examples: "golden hour laptop window", "small business owner sunset office", "hands typing dusk". Never brand names.
ai_prompt = one shot, one subject, magic hour, photoreal, vertical 9:16, no text. Start with: "cinematic still, magic hour, golden rim light, teal shadows,"
ai_video_prompt = same look + CAMERA MOVE only (slow push in, orbit, drone descend, parallax). 4 seconds. No dialogue. No text.
image_to_video_prompt = how to animate the matching ai_image: "slow cinematic push in, locked look, subtle dust in sunbeams, no morphing, no extra objects"
local_hint = 2-3 words matching files like laptop, desk, website, phone

Return JSON only, no markdown:
{"title":"","hook":"","script":"","caption":"","hashtags":["loopwork","automation","n8n"],"youtube_description":"","scenes":[{"id":1,"narration":"","visual_type":"pexels_video","pexels_query":"","ai_prompt":"","ai_video_prompt":"","image_to_video_prompt":"","local_hint":""}]}"""

CFG = "$('2. Config').first().json"
LOOP = "$('9. Loop each scene').item.json"
PARSE = "$('4. Extract script pack').first().json"
PAD = f"String({LOOP}.scene_no).padStart(2,'0')"
OUTDIR = f"{CFG}.outDir"


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


def sticky(name, text, pos, h=220, w=280, color=5):
    return node(
        name,
        "n8n-nodes-base.stickyNote",
        {"content": text, "height": h, "width": w, "color": color},
        pos,
        tv=1,
    )


def switch_rule(output_key, value, cid):
    return {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict",
                "version": 2,
            },
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
        "outputKey": output_key,
    }


def http_file(url_expr, timeout=120000):
    return {
        "url": url_expr,
        "options": {
            "timeout": timeout,
            "response": {"response": {"responseFormat": "file"}},
        },
    }


def http_json(url_expr, headers=None, timeout=120000):
    params = {"url": url_expr, "options": {"timeout": timeout}}
    if headers:
        params["sendHeaders"] = True
        params["headerParameters"] = {
            "parameters": [{"name": k, "value": v} for k, v in headers]
        }
    return params


mkdir_cmd = (
    "={{ \"powershell -NoProfile -Command \\\"New-Item -ItemType Directory -Force -Path '\" + "
    f"{OUTDIR}"
    + " + \"\\\\media','\" + "
    f"{OUTDIR}"
    + " + \"\\\\clips' | Out-Null\\\"\" }}"
)

ffmpeg_image = (
    "={{ \"ffmpeg -y -loop 1 -i \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\media\\\\scene_\" + "
    f"{PAD}"
    + " + \".jpg\\\" -t 7 -vf \\\"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30\\\" -an -c:v libx264 -pix_fmt yuv420p -preset veryfast \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\clips\\\\clip_\" + "
    f"{PAD}"
    + " + \".mp4\\\"\" }}"
)

ffmpeg_video = (
    "={{ \"ffmpeg -y -stream_loop -1 -i \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\media\\\\scene_\" + "
    f"{PAD}"
    + " + \".mp4\\\" -t 7 -vf \\\"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30\\\" -an -c:v libx264 -pix_fmt yuv420p -preset veryfast \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\clips\\\\clip_\" + "
    f"{PAD}"
    + " + \".mp4\\\"\" }}"
)

ffmpeg_final = (
    "={{ \"ffmpeg -y -f concat -safe 0 -i \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\clips\\\\concat.txt\\\" -i \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\voice.mp3\\\" -vf \\\"scale=1080:1920,format=yuv420p,drawtext=fontfile=C\\\\:/Windows/Fonts/arialbd.ttf:text=LOOP WORK:x=w-text_w-40:y=48:fontsize=32:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2\\\" -map 0:v:0 -map 1:a:0 -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k -shortest -movflags +faststart \\\"\" + "
    f"{OUTDIR}"
    + " + \"\\\\loop-work-reel.mp4\\\"\" }}"
)

save_visual_name = (
    "={{ "
    f"{OUTDIR}"
    + " + \"\\\\media\\\\scene_\" + "
    f"{PAD}"
    + " + \".\" + (['pexels_video','local'].includes("
    f"{LOOP}"
    + ".visual_type) ? 'mp4' : 'jpg') }}"
)

nodes = [
    sticky(
        "STEP 1",
        "## STEP 1 — Start\nForm or Test button.\nEmpty topic = Gemini picks.\n\nSelf-host n8n (npm), not Cloud.\nEnv keys: GEMINI_API_KEY, PEXELS_API_KEY\nInstall FFmpeg.",
        [-640, 120],
        h=280,
    ),
    node("1. Test in editor", "n8n-nodes-base.manualTrigger", {}, [-280, 160], tv=1),
    node(
        "1. Start from form",
        "n8n-nodes-base.formTrigger",
        {
            "formTitle": "Loop Work — create a Reel",
            "formDescription": "Leave Topic empty and Gemini picks a Loop Work idea.",
            "formFields": {
                "values": [
                    {
                        "fieldLabel": "Topic",
                        "fieldType": "text",
                        "placeholder": "5 n8n automations every local business needs",
                    },
                    {
                        "fieldLabel": "Notes",
                        "fieldType": "textarea",
                        "placeholder": "Optional: audience, offer, tone",
                    },
                ]
            },
            "options": {"buttonLabel": "Generate video"},
        },
        [-280, 360],
        extra={"webhookId": "loop-work-visual-factory"},
        tv=2.2,
    ),
    sticky(
        "STEP 2",
        "## STEP 2 — Config\nEdit rootPath if the folder moved.\nKeys stay in env vars.",
        [80, -40],
        h=180,
        color=4,
    ),
    node(
        "2. Config",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {"id": "root", "name": "rootPath", "value": ROOT_PATH, "type": "string"},
                    {
                        "id": "run",
                        "name": "runId",
                        "value": "={{ $now.toFormat('yyyyMMdd-HHmmss') }}",
                        "type": "string",
                    },
                    {
                        "id": "out",
                        "name": "outDir",
                        "value": "={{ '"
                        + ROOT_PATH.replace("\\", "\\\\")
                        + "' + '\\\\output\\\\' + $now.toFormat('yyyyMMdd-HHmmss') }}",
                        "type": "string",
                    },
                    {
                        "id": "model",
                        "name": "geminiModel",
                        "value": "gemini-2.5-flash",
                        "type": "string",
                    },
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [120, 240],
        tv=3.4,
    ),
    sticky(
        "STEP 3",
        "## STEP 3 — Script\nGemini writes title, hook, 6 scenes.\nEdit text inside **3. Script prompt**.",
        [420, -40],
        h=180,
        color=6,
    ),
    node(
        "3. Script prompt",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "sys",
                        "name": "systemPrompt",
                        "value": SYSTEM_PROMPT,
                        "type": "string",
                    },
                    {
                        "id": "usr",
                        "name": "userPrompt",
                        "value": "={{ 'Channel: Loop Work. Format: 9:16 reel.\\nTopic: ' + ($json.Topic || 'pick the strongest topic today about automation, website design, or digital marketing') + '\\nNotes: ' + ($json.Notes || 'none') + '\\nReturn JSON only.' }}",
                        "type": "string",
                    },
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [460, 240],
        tv=3.4,
    ),
    node(
        "3. Gemini write script",
        "n8n-nodes-base.httpRequest",
        {
            "method": "POST",
            "url": f"={{ 'https://generativelanguage.googleapis.com/v1beta/models/' + {CFG}.geminiModel + ':generateContent?key=' + $env.GEMINI_API_KEY }}",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [{"name": "Content-Type", "value": "application/json"}]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ systemInstruction: { parts: [{ text: $json.systemPrompt }] }, contents: [{ role: 'user', parts: [{ text: $json.userPrompt }] }], generationConfig: { temperature: 0.8, responseMimeType: 'application/json' } }) }}",
            "options": {"timeout": 120000},
        },
        [780, 240],
        tv=4.2,
    ),
    node(
        "4. Extract script pack",
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
            "includeOtherFields": False,
            "options": {},
        },
        [1100, 240],
        tv=3.4,
    ),
    sticky(
        "STEP 4",
        "## STEP 4 — Folders\nCreates output/run/media and clips.",
        [1360, -40],
        h=150,
        color=4,
    ),
    node("5. Create folders", "n8n-nodes-base.executeCommand", {"command": mkdir_cmd}, [1420, 240], tv=1),
    sticky(
        "STEP 5",
        "## STEP 5 — Voice\nFree Pollinations TTS.\nSaves voice.mp3",
        [1680, -40],
        h=150,
        color=7,
    ),
    node(
        "6. Generate voice",
        "n8n-nodes-base.httpRequest",
        http_file(
            f"={{ 'https://text.pollinations.ai/' + encodeURIComponent({PARSE}.pack.script) + '?model=openai-audio&voice=nova' }}",
            180000,
        ),
        [1740, 120],
        tv=4.2,
    ),
    node(
        "7. Save voice",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": f"={{ {OUTDIR} + '\\\\voice.mp3' }}", "options": {}},
        [2020, 120],
        tv=1,
    ),
    node(
        "7b. Reload pack",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "pack",
                        "name": "pack",
                        "value": f"={{ {PARSE}.pack }}",
                        "type": "object",
                    }
                ]
            },
            "options": {},
        },
        [2260, 120],
        tv=3.4,
    ),
    sticky(
        "STEP 6",
        "## STEP 6 — Visuals\nLoop 6 scenes:\nPexels video / Pexels photo / AI image / local sceneN.mp4\nThen FFmpeg clip.",
        [1740, 340],
        h=230,
        w=300,
        color=6,
    ),
    node(
        "8. Split scenes",
        "n8n-nodes-base.splitOut",
        {"fieldToSplitOut": "pack.scenes", "options": {}},
        [1740, 520],
        tv=1,
    ),
    node(
        "8. Number scenes",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "no",
                        "name": "scene_no",
                        "value": "={{ $itemIndex + 1 }}",
                        "type": "number",
                    }
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        [1980, 520],
        tv=3.4,
    ),
    node("9. Loop each scene", "n8n-nodes-base.splitInBatches", {"options": {}}, [2220, 520], tv=3),
    node(
        "10. Switch visual type",
        "n8n-nodes-base.switch",
        {
            "rules": {
                "values": [
                    switch_rule("pexels_video", "pexels_video", "sw1"),
                    switch_rule("pexels_photo", "pexels_photo", "sw2"),
                    switch_rule("ai_image", "ai_image", "sw3"),
                    switch_rule("local", "local", "sw4"),
                ]
            },
            "options": {"fallbackOutput": "extra"},
        },
        [2500, 520],
        tv=3.2,
    ),
    node(
        "11. Pexels video search",
        "n8n-nodes-base.httpRequest",
        http_json(
            f"={{ 'https://api.pexels.com/v1/videos/search?query=' + encodeURIComponent({LOOP}.pexels_query || {LOOP}.local_hint || 'laptop office') + '&orientation=portrait&per_page=5' }}",
            headers=[("Authorization", "={{ $env.PEXELS_API_KEY }}")],
        ),
        [2840, 80],
        tv=4.2,
    ),
    node(
        "11b. Pick video URL",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "u",
                        "name": "mediaUrl",
                        "value": "={{ $json.videos[0].video_files[0].link }}",
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        [3120, 80],
        tv=3.4,
    ),
    node(
        "11c. Download Pexels video",
        "n8n-nodes-base.httpRequest",
        http_file("={{ $json.mediaUrl }}"),
        [3400, 80],
        tv=4.2,
    ),
    node(
        "12. Pexels photo search",
        "n8n-nodes-base.httpRequest",
        http_json(
            f"={{ 'https://api.pexels.com/v1/search?query=' + encodeURIComponent({LOOP}.pexels_query || 'small business website') + '&orientation=portrait&per_page=5' }}",
            headers=[("Authorization", "={{ $env.PEXELS_API_KEY }}")],
        ),
        [2840, 300],
        tv=4.2,
    ),
    node(
        "12b. Pick photo URL",
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
        [3120, 300],
        tv=3.4,
    ),
    node(
        "12c. Download Pexels photo",
        "n8n-nodes-base.httpRequest",
        http_file("={{ $json.mediaUrl }}", 90000),
        [3400, 300],
        tv=4.2,
    ),
    node(
        "13. AI image",
        "n8n-nodes-base.httpRequest",
        http_file(
            f"={{ 'https://image.pollinations.ai/prompt/' + encodeURIComponent(({LOOP}.ai_prompt || 'cinematic dark teal workspace, photoreal, no text') + ', cinematic lighting, photoreal, no readable text, no watermark') + '?width=1080&height=1920&model=flux&nologo=true' }}",
            180000,
        ),
        [2840, 520],
        tv=4.2,
    ),
    node(
        "14. Read local file",
        "n8n-nodes-base.readWriteFile",
        {
            "operation": "read",
            "fileSelector": f"={{ {CFG}.rootPath + '\\\\assets\\\\local\\\\scene' + {LOOP}.scene_no + '.mp4' }}",
            "options": {},
        },
        [2840, 760],
        extra={"onError": "continueErrorOutput"},
        tv=1,
    ),
    node(
        "15. Save visual",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": save_visual_name, "options": {}},
        [3720, 400],
        tv=1,
    ),
    node(
        "16. Image or video clip?",
        "n8n-nodes-base.if",
        {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 2,
                },
                "conditions": [
                    {
                        "id": "img",
                        "leftValue": f"={{ ['ai_image','pexels_photo'].includes({LOOP}.visual_type) }}",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }
                ],
                "combinator": "and",
            }
        },
        [4000, 400],
        tv=2.2,
    ),
    node("17a. FFmpeg image clip", "n8n-nodes-base.executeCommand", {"command": ffmpeg_image}, [4320, 280], tv=1),
    node("17b. FFmpeg video clip", "n8n-nodes-base.executeCommand", {"command": ffmpeg_video}, [4320, 520], tv=1),
    node(
        "17c. Wait 8 sec",
        "n8n-nodes-base.wait",
        {"resume": "timeInterval", "amount": 8, "unit": "seconds"},
        [4640, 400],
        tv=1.1,
    ),
    sticky(
        "STEP 7",
        "## STEP 7 — Final video\nJoin 6 clips + voice + LOOP WORK logo.\nFile: loop-work-reel.mp4",
        [2220, 820],
        h=170,
        color=5,
    ),
    node(
        "18. Write concat list",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "c",
                        "name": "concatList",
                        "value": (
                            "={{ ['01','02','03','04','05','06'].map(n => \"file '\" + "
                            f"{OUTDIR}"
                            + ".replaceAll('\\\\','/') + '/clips/clip_' + n + \".mp4'\").join('\\n') }}"
                        ),
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        [2500, 900],
        tv=3.4,
    ),
    node(
        "18b. Concat to file",
        "n8n-nodes-base.convertToFile",
        {
            "operation": "toText",
            "sourceProperty": "concatList",
            "options": {"fileName": "concat.txt", "encoding": "utf8"},
        },
        [2780, 900],
        tv=1.1,
    ),
    node(
        "18c. Save concat.txt",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": f"={{ {OUTDIR} + '\\\\clips\\\\concat.txt' }}", "options": {}},
        [3060, 900],
        tv=1,
    ),
    node("19. Render final video", "n8n-nodes-base.executeCommand", {"command": ffmpeg_final}, [3340, 900], tv=1),
    node(
        "20. Write publish kit",
        "n8n-nodes-base.set",
        {
            "assignments": {
                "assignments": [
                    {
                        "id": "p",
                        "name": "publishText",
                        "value": (
                            "={{ 'LOOP WORK\\n\\nTITLE: ' + "
                            f"{PARSE}"
                            + ".pack.title + '\\nHOOK: ' + "
                            f"{PARSE}"
                            + ".pack.hook + '\\n\\nCAPTION\\n' + "
                            f"{PARSE}"
                            + ".pack.caption + '\\n' + (("
                            f"{PARSE}"
                            + ".pack.hashtags || []).map(t => '#' + String(t).replace('#','')).join(' ')) + '\\n\\nYOUTUBE\\n' + "
                            f"{PARSE}"
                            + ".pack.youtube_description + '\\n\\nSCRIPT\\n' + "
                            f"{PARSE}"
                            + ".pack.script }}"
                        ),
                        "type": "string",
                    },
                    {
                        "id": "v",
                        "name": "videoPath",
                        "value": f"={{ {OUTDIR} + '\\\\loop-work-reel.mp4' }}",
                        "type": "string",
                    },
                ]
            },
            "options": {},
        },
        [3660, 900],
        tv=3.4,
    ),
    node(
        "20b. Publish to file",
        "n8n-nodes-base.convertToFile",
        {
            "operation": "toText",
            "sourceProperty": "publishText",
            "options": {"fileName": "publish.txt", "encoding": "utf8"},
        },
        [3940, 900],
        tv=1.1,
    ),
    node(
        "20c. Save publish.txt",
        "n8n-nodes-base.writeBinaryFile",
        {"fileName": f"={{ {OUTDIR} + '\\\\publish.txt' }}", "options": {}},
        [4220, 900],
        tv=1,
    ),
]

connections = {
    "1. Test in editor": {"main": [[{"node": "2. Config", "type": "main", "index": 0}]]},
    "1. Start from form": {"main": [[{"node": "2. Config", "type": "main", "index": 0}]]},
    "2. Config": {"main": [[{"node": "3. Script prompt", "type": "main", "index": 0}]]},
    "3. Script prompt": {"main": [[{"node": "3. Gemini write script", "type": "main", "index": 0}]]},
    "3. Gemini write script": {"main": [[{"node": "4. Extract script pack", "type": "main", "index": 0}]]},
    "4. Extract script pack": {"main": [[{"node": "5. Create folders", "type": "main", "index": 0}]]},
    "5. Create folders": {"main": [[{"node": "6. Generate voice", "type": "main", "index": 0}]]},
    "6. Generate voice": {"main": [[{"node": "7. Save voice", "type": "main", "index": 0}]]},
    "7. Save voice": {"main": [[{"node": "7b. Reload pack", "type": "main", "index": 0}]]},
    "7b. Reload pack": {"main": [[{"node": "8. Split scenes", "type": "main", "index": 0}]]},
    "8. Split scenes": {"main": [[{"node": "8. Number scenes", "type": "main", "index": 0}]]},
    "8. Number scenes": {"main": [[{"node": "9. Loop each scene", "type": "main", "index": 0}]]},
    "9. Loop each scene": {
        "main": [
            [{"node": "18. Write concat list", "type": "main", "index": 0}],
            [{"node": "10. Switch visual type", "type": "main", "index": 0}],
        ]
    },
    "10. Switch visual type": {
        "main": [
            [{"node": "11. Pexels video search", "type": "main", "index": 0}],
            [{"node": "12. Pexels photo search", "type": "main", "index": 0}],
            [{"node": "13. AI image", "type": "main", "index": 0}],
            [{"node": "14. Read local file", "type": "main", "index": 0}],
            [{"node": "11. Pexels video search", "type": "main", "index": 0}],
        ]
    },
    "11. Pexels video search": {"main": [[{"node": "11b. Pick video URL", "type": "main", "index": 0}]]},
    "11b. Pick video URL": {"main": [[{"node": "11c. Download Pexels video", "type": "main", "index": 0}]]},
    "11c. Download Pexels video": {"main": [[{"node": "15. Save visual", "type": "main", "index": 0}]]},
    "12. Pexels photo search": {"main": [[{"node": "12b. Pick photo URL", "type": "main", "index": 0}]]},
    "12b. Pick photo URL": {"main": [[{"node": "12c. Download Pexels photo", "type": "main", "index": 0}]]},
    "12c. Download Pexels photo": {"main": [[{"node": "15. Save visual", "type": "main", "index": 0}]]},
    "13. AI image": {"main": [[{"node": "15. Save visual", "type": "main", "index": 0}]]},
    "14. Read local file": {
        "main": [
            [{"node": "15. Save visual", "type": "main", "index": 0}],
            [{"node": "11. Pexels video search", "type": "main", "index": 0}],
        ]
    },
    "15. Save visual": {"main": [[{"node": "16. Image or video clip?", "type": "main", "index": 0}]]},
    "16. Image or video clip?": {
        "main": [
            [{"node": "17a. FFmpeg image clip", "type": "main", "index": 0}],
            [{"node": "17b. FFmpeg video clip", "type": "main", "index": 0}],
        ]
    },
    "17a. FFmpeg image clip": {"main": [[{"node": "17c. Wait 8 sec", "type": "main", "index": 0}]]},
    "17b. FFmpeg video clip": {"main": [[{"node": "17c. Wait 8 sec", "type": "main", "index": 0}]]},
    "17c. Wait 8 sec": {"main": [[{"node": "9. Loop each scene", "type": "main", "index": 0}]]},
    "18. Write concat list": {"main": [[{"node": "18b. Concat to file", "type": "main", "index": 0}]]},
    "18b. Concat to file": {"main": [[{"node": "18c. Save concat.txt", "type": "main", "index": 0}]]},
    "18c. Save concat.txt": {"main": [[{"node": "19. Render final video", "type": "main", "index": 0}]]},
    "19. Render final video": {"main": [[{"node": "20. Write publish kit", "type": "main", "index": 0}]]},
    "20. Write publish kit": {"main": [[{"node": "20b. Publish to file", "type": "main", "index": 0}]]},
    "20b. Publish to file": {"main": [[{"node": "20c. Save publish.txt", "type": "main", "index": 0}]]},
}

workflow = {
    "name": "Loop Work — Content Factory",
    "nodes": nodes,
    "connections": connections,
    "active": False,
    "settings": {"executionOrder": "v1"},
    "versionId": "loop-work-factory-visual-v2",
    "meta": {"templateCredsSetupCompleted": True},
    "id": "loopWorkContentFactory",
    "tags": [],
}

for i, n in enumerate(workflow["nodes"]):
    n["id"] = f"lw{i:03d}"

OUT.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
print(f"Wrote {OUT} with {len(nodes)} nodes")
