const vscode = require('vscode');
const fs = require('fs').promises;
const path = require('path');

let contextGlobal = undefined;

function activate(context) {
    contextGlobal = context;
    const LOG_FILE = path.join(context.globalStorageUri.fsPath, 'jemai_chat_log.jsonl');

    fs.mkdir(path.dirname(LOG_FILE), {recursive:true}).then(()=>fs.appendFile(LOG_FILE,'')).catch(()=>{});

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('jemaiChatSidebar', {
            async resolveWebviewView(webviewView) {
                webviewView.webview.options = { enableScripts: true };
                let items = await readAllChat(LOG_FILE);
                webviewView.webview.html = getWebviewHtml(items);

                webviewView.webview.onDidReceiveMessage(async msg => {
                    if (msg.type === 'exportChat') {
                        await exportChatHistory(LOG_FILE, msg.format, context);
                    } else if (msg.type === 'copyChat') {
                        await copyChatHistory(LOG_FILE);
                    } else if (msg.type === 'copyLastReply') {
                        await copyLastReply(LOG_FILE);
                    } else if (msg.type === 'pasteLastReply') {
                        await pasteLastReply(LOG_FILE);
                    } else if (msg.type === 'copyMsg' && typeof msg.idx === 'number') {
                        const items = await readAllChat(LOG_FILE);
                        if(items[msg.idx]) {
                            await vscode.env.clipboard.writeText(items[msg.idx].content);
                            vscode.window.showInformationMessage('This reply copied to clipboard!');
                        }
                    }
                });

                const fileWatcher = vscode.workspace.createFileSystemWatcher(LOG_FILE);
                fileWatcher.onDidChange(async () => {
                    let items = await readAllChat(LOG_FILE);
                    webviewView.webview.html = getWebviewHtml(items);
                });
                context.subscriptions.push(fileWatcher);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('jemai.openChatGPTWeb', () => {
            const panel = vscode.window.createWebviewPanel(
                'chatgptWeb',
                'ChatGPT Web',
                vscode.ViewColumn.Beside,
                {
                    enableScripts: true,
                    retainContextWhenHidden: true
                }
            );
            const targetURL = 'https://chat.openai.com/';
            panel.webview.html = `
                <html>
                  <body>
                    <h2>ChatGPT (Web)</h2>
                    <iframe src="${targetURL}" width="100%" height="700" style="min-height:100vh;border: 2px solid #888"></iframe>
                    <div>If you cannot see ChatGPT (browser blocked embedding), <a href="#" onclick="vscode.postMessage({type: 'openExternally'})">open in browser</a></div>
                    <script>
                      const vscode = acquireVsCodeApi();
                      window.addEventListener('message', e => {
                        if (e.data.type === 'openExternally') {
                          vscode.postMessage({ type: 'openExternally' });
                        }
                      });
                    </script>
                  </body>
                </html>
            `;
            panel.webview.onDidReceiveMessage(msg => {
                if (msg.type === 'openExternally') {
                    vscode.env.openExternal(vscode.Uri.parse(targetURL));
                }
            });
        })
    );

    setInterval(async () => {
        let clipboard = await vscode.env.clipboard.readText();
        if (
            clipboard && clipboard.length > 24 &&
            (clipboard.includes('OpenAI') || clipboard.includes('JEMAI')) &&
            vscode.window.activeTextEditor
        ) {
            vscode.window.showInformationMessage(
                'Clipboard looks like an AI chat reply. Paste into editor?', 'Paste'
            ).then(choice => {
                if (choice === 'Paste')
                    vscode.window.activeTextEditor.edit(editBuilder =>
                        editBuilder.insert(
                            vscode.window.activeTextEditor.selection.active, clipboard
                        )
                    );
            });
        }
    }, 10000);
}

async function readAllChat(LOG_FILE) {
    try {
        const data = await fs.readFile(LOG_FILE, 'utf8');
        return data.split('\n').filter(Boolean).map(line => JSON.parse(line));
    } catch (e) { return []; }
}

async function exportChatHistory(LOG_FILE, format, context) {
    const items = await readAllChat(LOG_FILE);
    let text, ext;
    if (format === 'txt') {
        text = items.map(item => `[${item.role}] ${item.content}`).join('\n');
        ext = 'txt';
    } else if (format === 'md') {
        text = items
            .map(item =>
                item.role === 'assistant'
                    ? `**JEMAI:** ${item.content}`
                    : `**You:** ${item.content}`
            ).join('\n\n');
        ext = 'md';
    } else {
        text = items.map(i => JSON.stringify(i)).join('\n');
        ext = 'jsonl';
    }
    const uri = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file(path.join(context.globalStoragePath, `jemai_chat_export.${ext}`)),
        saveLabel: 'Export',
        filters: { 'All Files': ['*'] }
    });
    if (uri) {
        await fs.writeFile(uri.fsPath, text, 'utf8');
        vscode.window.showInformationMessage(`JEMAI chat log exported: ${uri.fsPath}`);
    }
}

async function copyChatHistory(LOG_FILE) {
    const items = await readAllChat(LOG_FILE);
    const text = items.map(item => `[${item.role}] ${item.content}`).join('\n');
    await vscode.env.clipboard.writeText(text);
    vscode.window.showInformationMessage('JEMAI chat copied to clipboard!');
}

async function copyLastReply(LOG_FILE) {
    const items = await readAllChat(LOG_FILE);
    const last = [...items].reverse().find(x=>x.role==="assistant"||x.role==="ai"||x.role==="jemai");
    if (last) {
        await vscode.env.clipboard.writeText(last.content);
        vscode.window.showInformationMessage('Last JEMAI reply copied!');
    }
}

async function pasteLastReply(LOG_FILE) {
    const items = await readAllChat(LOG_FILE);
    const last = [...items].reverse().find(x=>x.role==="assistant"||x.role==="ai"||x.role==="jemai");
    if (last && vscode.window.activeTextEditor) {
        await vscode.window.activeTextEditor.edit(editBuilder => {
            editBuilder.insert(vscode.window.activeTextEditor.selection.active, last.content);
        });
        vscode.window.showInformationMessage('Last JEMAI reply inserted into editor!');
    }
}

function getWebviewHtml(items=[]) {
    return `
<!DOCTYPE html>
<html>
<head>
<style>
html,body { font-family: Menlo,monospace; font-size:1rem; color:#232; background:#fafafa;}
.msg { padding:8px; border-bottom:1px solid #eee; margin-bottom:0; }
.user { color: #284; }
.ai { color: #0088cc;}
small { color:#aaa;}
button { margin-right:3px; margin-bottom:6px;}
code { background:#eee;padding:2px 4px; }
pre { background:#f6f6f6; padding:8px;}
</style>
</head>
<body>
${items.map((msg, idx) => `
  <div class="msg ${msg.role==='assistant'?'ai':'user'}">
    <b>${msg.role==='assistant'?'🤖 JEMAI':'🧑 You'}</b>
    <small>${msg.time||''}</small>
    <div>${formatContent(msg.content)}</div>
    ${msg.role==='assistant'? `<button onclick="window.copyMsg(${idx})">Copy</button>`:""}
  </div>
`).join('')}
  <div style="margin:10px 0;">
    <button onclick="vscode.postMessage({ type: 'exportChat', format:'txt' })">Export .txt</button>
    <button onclick="vscode.postMessage({ type: 'exportChat', format:'md' })">Export .md</button>
    <button onclick="vscode.postMessage({ type: 'exportChat', format:'jsonl' })">Export .jsonl</button>
    <button onclick="vscode.postMessage({ type: 'copyChat' })">Copy All</button>
    <button onclick="vscode.postMessage({ type: 'copyLastReply' })">Copy Last</button>
    <button onclick="vscode.postMessage({ type: 'pasteLastReply' })">↳ Paste Last to Editor</button>
  </div>
<script>
const vscode = acquireVsCodeApi();
window.copyMsg = idx => vscode.postMessage({type:'copyMsg', idx});
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
}
function formatContent(str) {
  return escapeHtml(str)
    .replace(/```([\s\S]+?)```/g, m=>'<pre><code>'+m.slice(3,-3)+'</code></pre>')
    .replace(/\n/g,"<br>");
}
</script>
</body>
</html>
`
}

exports.activate = activate;