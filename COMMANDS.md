# SHADOW — Command Reference

SHADOW understands plain English. Type your request in the text box (or say
it, once voice mode is enabled) and it will figure out what to do. Below are
the kinds of things you can currently ask.

---

## Open an app, file, or website
The catch-all "open X" command. SHADOW tries these in order:
1. Is X an installed application?
2. Is X a known website (Instagram, YouTube, Gmail, GitHub, etc.)?
3. Is X a file somewhere in your Desktop / Documents / Downloads / Pictures /
   Videos / Music?

**Examples:**
- `open chrome`
- `open vs code`
- `open notepad`
- `open whatsapp` — opens the desktop app if installed, otherwise WhatsApp Web
- `open telegram`
- `open instagram` — opens instagram.com directly
- `open resume` — searches your folders and opens it if there's one clear match
- `open project report` — if multiple files match, SHADOW lists them so you
  can be more specific instead of guessing

`launch X` and `start X` work the same as `open X`.

---

## Close an app
- `close chrome`
- `quit spotify`
- `exit notepad`

---

## Open a website directly
Use this when you already have an exact URL or domain in mind.
- `open github.com`
- `go to youtube.com`
- `visit https://example.com`

---

## Create a folder
- `create folder called Projects`
- `create folder called Projects in Downloads`
- `make a folder named Invoices in Documents`

---

## Search for files
- `find PDFs in Downloads`
- `find *.py in Documents`
- `search for resume in Desktop`
- `find all images in Pictures`

---

## Read a file
- `read C:\Users\yourname\Desktop\notes.txt`
- `open and read notes.txt`

---

## Safety — what happens with risky actions
Every command is checked before it runs:
- **Low risk** (opening apps/files, searching, reading) — runs immediately.
- **Medium risk** (moving/renaming files, closing apps) — runs, but can be
  set to require confirmation.
- **High risk** (deleting files/folders, system commands) — SHADOW always
  stops and asks "yes/no" before doing it. There's no way to skip this.

---

## Not supported yet
- Moving, copying, renaming, or deleting files by typing a command (the
  underlying tools exist, but there's no natural-language trigger for them
  yet)
- Multi-step requests like "open VS Code and open my project"
- Voice input/output (coming in a later update)
- Browser actions beyond opening a page (clicking, typing, searching in-page)

If SHADOW doesn't understand a request, it will say so and suggest
rephrasing rather than guessing.