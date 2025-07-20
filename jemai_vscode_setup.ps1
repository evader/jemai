# JEMAI AGI OS VSCode Extension Builder
# Save as jemai_vscode_setup.ps1 and run in PowerShell (not admin) from C:\JEMAI_HUB

# Create folders
New-Item -ItemType Directory -Name "jemai_vscode" -Force | Out-Null
New-Item -ItemType Directory -Path ".\jemai_vscode\media" -Force | Out-Null

# Write package.json
@'
{
  "name": "jemai-agi-os",
  "displayName": "JEMAI AGI OS",
  "description": "Seamlessly connect VSCode to your local JEMAI AGI OS: send code, chat, trigger macros, and more.",
  "version": "1.0.0",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": [
    "Other"
  ],
  "icon": "media/jemai_chip_icon.png",
  "activationEvents": [
    "onCommand:jemai.sendSelection",
    "onCommand:jemai.openChat"
  ],
  "contributes": {
    "commands": [
      {
        "command": "jemai.sendSelection",
        "title": "Send Selection to JEMAI AGI"
      },
      {
        "command": "jemai.openChat",
        "title": "Open JEMAI AGI Chat"
      }
    ],
    "menus": {
      "editor/context": [
        {
          "command": "jemai.sendSelection",
          "when": "editorHasSelection",
          "group": "navigation@100"
        }
      ]
    }
  },
  "main": "./extension.js"
}
'@ | Set-Content .\jemai_vscode\package.json -Encoding UTF8

# Write extension.js
@'
const vscode = require('vscode');
const fetch = require('node-fetch');
const path = require('path');

function activate(context) {
    // Send selection to JEMAI AGI
    let sendCmd = vscode.commands.registerCommand('jemai.sendSelection', async function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) { return; }
        const code = editor.document.getText(editor.selection) || editor.document.getText();
        if (!code.trim()) {
            vscode.window.showWarningMessage('No code selected or in file!');
            return;
        }
        // Send to backend, no prompt, "just do it"
        try {
            let res = await fetch('http://localhost:8181/api/from_chrome', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code, action: 'justdoit', source: 'vscode' })
            });
            let j = await res.json();
            vscode.window.showInformationMessage(j.resp || 'Sent to JEMAI.');
        } catch (e) {
            vscode.window.showErrorMessage('Failed to contact JEMAI AGI backend.');
        }
    });

    // Chat sidebar panel
    let chatPanelCmd = vscode.commands.registerCommand('jemai.openChat', () => {
        const panel = vscode.window.createWebviewPanel(
            'jemaiChat', 'JEMAI AGI Chat', vscode.ViewColumn.Beside, {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.file(path.join(context.extensionPath, 'media'))]
            }
        );
        const bannerUri = panel.webview.asWebviewUri(vscode.Uri.file(path.join(context.extensionPath, 'media', 'banner_main.png')));
        const iconUri = panel.webview.asWebviewUri(vscode.Uri.file(path.join(context.extensionPath, 'media', 'jemai_chip_icon.png')));
        panel.webview.html = getWebviewContent(bannerUri, iconUri);
        // Handle chat messages
        panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.type === 'chat') {
                try {
                    let res = await fetch('http://localhost:8181/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ q: msg.text })
                    });
                    let j = await res.json();
                    panel.webview.postMessage({ type: 'response', text: j.resp });
                } catch {
                    panel.webview.postMessage({ type: 'response', text: '[JEMAI backend unreachable]' });
                }
            }
        });
    });

    context.subscriptions.push(sendCmd, chatPanelCmd);
}
exports.activate = activate;

function getWebviewContent(bannerUri, iconUri) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>JEMAI AGI Chat</title>
    <style>
        body { background: #ffe6d0; color: #312f2f; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; }
        .banner { width: 100%; display: flex; align-items: center; background: #ffe6d0; }
        .banner img { height: 64px; margin: 14px 20px 14px 20px; }
        .jemai-title { font-size: 1.8em; font-weight: bold; color: #775643; }
        .chatbox { margin: 18px; border-radius: 12px; background: #e2e2ea; min-height: 220px; max-height: 320px; overflow-y: auto; padding: 20px; }
        .user { color: #2f323b; font-weight: 600; }
        .resp { color: #35506b; margin-top: 8px; }
        .bar { display: flex; margin: 0 18px 18px 18px; }
        .inp { flex:1; border-radius: 8px; border: none; padding: 12px; font-size: 1em; }
        .send { background: #775643; color: #fff; border: none; border-radius: 8px; margin-left: 10px; padding: 12px 24px; font-weight: 700; cursor: pointer;}
    </style>
</head>
<body>
    <div class="banner">
        <img src="${bannerUri}" alt="JEMAI Banner">
        <span class="jemai-title">JEMAI AGI OS — WarmWinds</span>
    </div>
    <div class="chatbox" id="chatbox"></div>
    <div class="bar">
        <input class="inp" id="chatinp" placeholder="Ask anything..." />
        <button class="send" onclick="sendMsg()">Send</button>
    </div>
    <script>
        const chatbox = document.getElementById('chatbox');
        const chatinp = document.getElementById('chatinp');
        function sendMsg() {
            const text = chatinp.value.trim();
            if (!text) return;
            chatbox.innerHTML += '<div class="user">You: ' + text + '</div>';
            chatinp.value = '';
            window.parent.postMessage({ type: 'chat', text: text }, '*');
            window.acquireVsCodeApi().postMessage({ type: 'chat', text });
        }
        window.addEventListener('message', event => {
            const msg = event.data;
            if (msg.type === 'response') {
                chatbox.innerHTML += '<div class="resp">JEMAI: ' + msg.text + '</div>';
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        });
        chatinp.addEventListener('keydown', e => { if(e.key==='Enter') sendMsg(); });
    </script>
</body>
</html>
`;
}
'@ | Set-Content .\jemai_vscode\extension.js -Encoding UTF8

# Write README.md
@'
# JEMAI AGI OS VSCode Extension

- Right-click code or select code > Command Palette > “Send Selection to JEMAI AGI” — Instantly triggers your local AGI OS.
- Open the “JEMAI AGI Chat” panel from the Command Palette — Chat directly with your local backend.
- Uses your AGI branding, banner, and icon.

How to install:
1. cd jemai_vscode
2. npm install (to get dependencies like node-fetch, if not included)
3. Press F5 in VSCode to “Run Extension” (or package with vsce)
4. Connects to http://localhost:8181 by default.

Requires:
- Your jemai.py backend running on localhost:8181
- Your media/ images in the extension directory
'@ | Set-Content .\jemai_vscode\README.md -Encoding UTF8

Write-Host "`n[!] MANUAL: Copy banner_main.png and jemai_chip_icon.png from C:\JEMAI_HUB\static\ to C:\JEMAI_HUB\jemai_vscode\media\`n"
Write-Host "[OK] VSCode extension skeleton created! Open C:\JEMAI_HUB\jemai_vscode in VSCode, then run 'npm install', and continue to the test steps."
