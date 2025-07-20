const vscode = require('vscode');
const fetch = require('node-fetch');
const path = require('path');

function activate(context) {
    let sendCmd = vscode.commands.registerCommand('jemai.sendSelection', async function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) { return; }
        const code = editor.document.getText(editor.selection) || editor.document.getText();
        if (!code.trim()) {
            vscode.window.showWarningMessage('No code selected or in file!');
            return;
        }
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
`;}
