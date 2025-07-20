# JEMAI AGI OS VSCode Extension

- Right-click code or select code > Command Palette > â€œSend Selection to JEMAI AGIâ€ â€” Instantly triggers your local AGI OS.
- Open the â€œJEMAI AGI Chatâ€ panel from the Command Palette â€” Chat directly with your local backend.
- Uses your AGI branding, banner, and icon.

How to install:
1. cd jemai_vscode
2. npm install (to get dependencies like node-fetch, if not included)
3. Press F5 in VSCode to â€œRun Extensionâ€ (or package with vsce)
4. Connects to http://localhost:8181 by default.

Requires:
- Your jemai.py backend running on localhost:8181
- Your media/ images in the extension directory
