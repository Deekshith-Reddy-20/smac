# Loop Work — n8n content factory (step by step)

Main workflow (this is the one that matches your system):

**`workflows/Loop-Work-Calendar-Drive.json`**

Sheet calendar → 1 topic/day → script → split visuals (AI image / AI video / stock) → TTS → final video → Google Drive. The Sheet updates when the script is ready and again when files are in Drive.

30-day calendar file: `sheet/30-day-content-calendar.csv`  
Import that CSV into Google Sheets, name the tab **Calendar**.

## Import

1. n8n on this PC (Cloud cannot run FFmpeg):
   ```powershell
   npm install -g n8n
   n8n
   ```
2. Open http://localhost:5678
3. Import **`Loop-Work-Calendar-Drive.json`**
4. In **2. Config** paste:
   - Google Sheet ID
   - Drive parent folder ID
5. On every Google Sheets / Drive node: click and connect your Google login
6. Set Windows env: `GEMINI_API_KEY`, `PEXELS_API_KEY`, optional `POLLINATIONS_KEY` (free AI video)

Enable **1. Every morning** when you want 1 video per day. Until then use **Test in editor**.

---

This is an **n8n canvas**, not a Python app. Import the JSON, then follow the numbered nodes.

## Keys (free)

Set these as **Windows environment variables**, then restart n8n:

| Variable | Get it |
|----------|--------|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `PEXELS_API_KEY` | https://www.pexels.com/api/ |

Install FFmpeg:

```powershell
winget install Gyan.FFmpeg
```

Close the terminal after install.

Put extra Pexels clips in `assets/local` named `scene1.mp4` … `scene6.mp4`. If a file is missing, that scene uses Pexels instead.

If you moved this folder, open node **2. Config** and change `rootPath`.

---

## Content Factory — what each node does

Read the yellow notes on the canvas. The flow is:

**STEP 1 — Start**  
`1. Start from form` or `1. Test in editor`  
Type a topic, or leave it empty.

**STEP 2 — Config**  
`2. Config`  
Sets the Loop Work folder and output path.

**STEP 3 — Topic to script**  
`3. Script prompt` ← edit the writing style here  
`3. Gemini write script` ← free Gemini  
`4. Extract script pack` ← title, hook, 6 scenes

**STEP 4 — Folders**  
`5. Create folders`  
Makes `output\<time>\media` and `clips`.

**STEP 5 — Script to voice**  
`6. Generate voice` ← free Pollinations TTS  
`7. Save voice` → `voice.mp3`

**STEP 6 — Script to visuals**  
`8. Split scenes` → `9. Loop each scene` → `10. Switch visual type`

| Switch output | Node | What you get |
|---------------|------|----------------|
| pexels_video | `11.` search + download | Real stock video |
| pexels_photo | `12.` search + download | Real stock photo |
| ai_image | `13. AI image` | Pollinations image |
| local | `14. Read local file` | Your `sceneN.mp4` |

Then:

- `15. Save visual`
- `16. Image or video clip?`
- `17a` / `17b` FFmpeg → 7-second 9:16 clip
- `17c. Wait 8 sec` (free API limit) → next scene

**STEP 7 — Visuals to final video**  
`18` concat list  
`19. Render final video` → `loop-work-reel.mp4` with **LOOP WORK** logo  
`20` save `publish.txt` (caption, hashtags, description)

Finished files: `loop-work/output\<timestamp>\`

---

## Topic Ideas workflow

Use this first when you do not know what to post.

1. Start  
2. Config (Gemini model)  
3. `Gemini (free)` returns 10 hooks  
4. Pick one topic → paste it into the Content Factory form

---

## Run

Open **Loop Work — Content Factory** → **Test workflow**.  
First run takes a few minutes (6 scenes + voice + FFmpeg).
