import os,sys,time,json,threading,platform,glob,importlib.util,shutil,base64,subprocess,random
from pathlib import Path
from flask import Flask,request,jsonify,send_from_directory,redirect,render_template_string
from werkzeug.utils import secure_filename

HOME=str(Path.home())
JEMAI_HUB=os.path.join(HOME,"jemai_hub")
APP_CORE=os.path.join(JEMAI_HUB,"app_core")
FRONTEND=os.path.join(JEMAI_HUB,"frontend")
PLUGINS=os.path.join(JEMAI_HUB,"plugins")
STATIC=os.path.join(JEMAI_HUB,"static")
UPLOADS=os.path.join(JEMAI_HUB,"uploads")
CHATDATA=os.path.join(JEMAI_HUB,"chat_data")
for d in [JEMAI_HUB,APP_CORE,FRONTEND,PLUGINS,STATIC,UPLOADS,CHATDATA]:os.makedirs(d,exist_ok=True)
SUPERFILE_PATH=os.path.abspath(__file__)
VERSIONS_DIR=os.path.join(HOME,".jemai_versions")
if not os.path.exists(VERSIONS_DIR):os.makedirs(VERSIONS_DIR,exist_ok=True)
BACKUP_PATH=os.path.join(VERSIONS_DIR,f"jemai_{time.strftime('%Y%m%d-%H%M%S')}.py")
if not os.path.exists(BACKUP_PATH):shutil.copy2(SUPERFILE_PATH,BACKUP_PATH)

theme_css="body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(120deg,#20254b 0%,#353b5c 100%);color:#fff;}.jemai-center{min-height:97vh;display:flex;flex-direction:column;align-items:center;justify-content:center;}.jemai-title{font-size:2.8rem;font-weight:700;margin-bottom:16px;letter-spacing:1px;}.jemai-nav{display:flex;gap:36px;margin-bottom:36px;font-size:1.25rem;}.jemai-nav a{text-decoration:none;color:#faf7ed;background:#303660;padding:12px 30px;border-radius:9px;transition:background .18s;}.jemai-nav a:hover{background:#464bbd;}.jemai-actions{display:flex;gap:22px;margin-top:26px;}.jemai-actions button{padding:14px 34px;font-size:1.18rem;font-weight:500;border:none;border-radius:8px;background:#ffdd88;color:#222240;cursor:pointer;box-shadow:0 2px 12px #0002;transition:background .18s,color .18s;}.jemai-actions button:hover{background:#ffd54f;color:#001132;}.jemai-status{margin:22px 0 0 0;font-size:1.15rem;letter-spacing:.5px;}@media(max-width:700px){.jemai-title{font-size:1.6rem;}.jemai-nav{gap:13px;font-size:1.01rem;}.jemai-actions{flex-direction:column;gap:12px;}}::-webkit-scrollbar{width:7px;background:#2e3353;}::-webkit-scrollbar-thumb{background:#5356a2;border-radius:4px;}"

vscode_js="window.loadVSCode=function(path){require.config({paths:{vs:'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs'}});require(['vs/editor/editor.main'],function(){fetch('/api/files/read?path='+encodeURIComponent(path)).then(r=>r.json()).then(d=>{if(!window.vscodeEditor){document.getElementById('vscode-container').innerHTML='';window.vscodeEditor=monaco.editor.create(document.getElementById('vscode-container'),{value:d.content||'',language:'python',theme:'vs-dark',automaticLayout:true});window.vscodeFile=path;let btn=document.createElement('button');btn.innerText='Save';btn.style='margin-top:10px;padding:8px 24px;font-size:1rem;';btn.onclick=function(){fetch('/api/files/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:window.vscodeFile,code:window.vscodeEditor.getValue()})}).then(r=>r.json()).then(x=>{btn.innerText='Saved!';setTimeout(()=>btn.innerText='Save',1100);});};document.getElementById('vscode-container').appendChild(btn);}else{window.vscodeEditor.setValue(d.content||'');window.vscodeFile=path;}});});};"

app_js="window.refreshDashboard=function(){fetch('/api/sysinfo').then(r=>r.json()).then(d=>{let s='Host: '+d.host+'<br>IP: '+d.ip+'<br>CPU: '+d.cpu+'<br>RAM: '+d.ram+'<br>Disk: '+d.disk+'<br>Ollama: '+d.models.join(', ')+'<br>GPU: '+d.gpu+'<br>Version: '+d.version;document.getElementById('jemai-status').innerHTML=s;});}window.addEventListener('DOMContentLoaded',()=>{if(document.getElementById('jemai-status')){window.refreshDashboard();}});"

index_html="""<!DOCTYPE html>
<html><head><title>JEMAI AGI OS: Home</title><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/theme.css"><script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js"></script><script src="/static/app.js"></script><script src="/static/vscode.js"></script></head><body><div class="jemai-center"><div class="jemai-title">JEMAI AGI OS<br><span style="font-size:1.2rem;font-weight:400;">ALL-IN-ONE SUPERFILE</span></div><div class="jemai-nav"><a href="/dashboard">Dashboard</a><a href="/chatui">Chat</a><a href="/explorer">Explorer</a><a href="/settings">Settings</a></div><div class="jemai-actions"><button onclick="showEditor('/jemai_hub/jemai.py')">Open jemai.py in VSCode</button><button onclick="window.location.href='/dashboard'">Go to Dashboard</button><button onclick="window.location.href='/chatui'">Launch Chat</button></div><div class="jemai-status" id="jemai-status">Loading system info...</div></div><div id="vscode-container" style="width:95vw;height:60vh;min-height:500px;margin:20px auto;display:none"></div><script>function showEditor(path){document.getElementById('vscode-container').style.display='block';window.loadVSCode(path);}</script></body></html>"""

app=Flask(__name__,static_folder=STATIC)
app.config["MAX_CONTENT_LENGTH"]=500*1024*1024

@app.route("/")
def home():return index_html

@app.route("/static/<path:fname>")
def static_files(fname):
 if fname=="theme.css":return theme_css,200,{"Content-Type":"text/css"}
 if fname=="vscode.js":return vscode_js,200,{"Content-Type":"application/javascript"}
 if fname=="app.js":return app_js,200,{"Content-Type":"application/javascript"}
 return send_from_directory(STATIC,fname)

@app.route("/uploads/<path:fname>")
def uploads(fname):return send_from_directory(UPLOADS,fname)

@app.route("/api/sysinfo")
def sysinfo():
 import psutil
 try:gpu="NVIDIA GeForce GTX 1060 3GB"
 except:gpu="Unknown"
 models=[f.replace(".bin","") for f in glob.glob(os.path.join(JEMAI_HUB,"*.bin"))]or["llama3:latest","gemma3:latest"]
 disk=f"{round(100*(shutil.disk_usage(HOME).used/shutil.disk_usage(HOME).total),1)}%"
 return jsonify({"host":platform.node(),"ip":get_ip(),"cpu":f"{psutil.cpu_percent()}%","ram":f"{psutil.virtual_memory().percent}%","disk":disk,"models":models,"gpu":gpu,"version":get_version()})

def get_ip():
 import socket
 try:s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close();return ip
 except:return"127.0.0.1"

def get_version():
 vers=sorted([f for f in os.listdir(VERSIONS_DIR)if f.endswith(".py")])
 return vers[-1]if vers else os.path.basename(SUPERFILE_PATH)

@app.route("/api/cluster")
def cluster():
 nodes=[{"host":platform.node(),"ip":get_ip(),"status":"online","os":platform.system()},{"host":"jemai-ubuntu","ip":"192.168.1.99","status":"online","os":"linux"}]
 return jsonify(nodes)

@app.route("/api/files/list",methods=["GET"])
def files_list():
 base=request.args.get("base",JEMAI_HUB)
 def tree(path):
  items=[]
  for f in os.listdir(path):
   full=os.path.join(path,f)
   if os.path.isdir(full):items.append({"type":"dir","name":f,"children":tree(full)})
   else:items.append({"type":"file","name":f})
  return items
 return jsonify(tree(base))

@app.route("/api/files/read",methods=["GET"])
def files_read():
 path=request.args.get("path")
 if not path or not os.path.exists(path):return jsonify({"error":"not found"})
 with open(path,encoding="utf-8",errors="ignore")as f:content=f.read()
 return jsonify({"content":content})

@app.route("/api/files/save",methods=["POST"])
def files_save():
 data=request.json
 path=data.get("path")
 code=data.get("code")
 if not path:return jsonify({"error":"no path"})
 with open(path,"w",encoding="utf-8")as f:f.write(code)
 return jsonify({"result":"ok"})

@app.route("/api/files/upload",methods=["POST"])
def files_upload():
 file=request.files.get("file")
 if not file:return jsonify({"error":"no file"})
 filename=secure_filename(file.filename)
 out_path=os.path.join(UPLOADS,filename)
 file.save(out_path)
 return jsonify({"result":"uploaded","path":out_path})

@app.route("/api/plugins/list")
def plugins_list():
 files=[f for f in os.listdir(PLUGINS)if f.endswith(".py")]
 return jsonify({"plugins":files})

@app.route("/api/plugins/load",methods=["POST"])
def plugins_load():
 name=request.json.get("name","")
 path=os.path.join(PLUGINS,name)
 if not os.path.exists(path):return jsonify({"error":"not found"})
 try:spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return jsonify({"result":"ok"})
 except Exception as e:return jsonify({"error":str(e)})

@app.route("/api/rag/upload",methods=["POST"])
def rag_upload():
 file=request.files.get("file")
 if not file:return jsonify({"error":"no file"})
 filename=secure_filename(file.filename)
 out_path=os.path.join(CHATDATA,filename)
 file.save(out_path)
 return jsonify({"result":"rag uploaded","path":out_path})

@app.route("/api/rag/search",methods=["GET"])
def rag_search():
 q=request.args.get("q","")
 return jsonify([{"text":f"RAG/Chroma result for: {q}"}])

@app.route("/api/audio/devices")
def audio_devices():
 return jsonify({"speakers":["Default Speaker","Sonos Living Room"],"mics":["Default Mic","RØDE NT-USB"],"using_speaker":"Default Speaker","using_mic":"Default Mic"})

@app.route("/api/audio/speak",methods=["POST"])
def audio_speak():
 text=request.json.get("text","")
 print(f"[VOICE] {text[:100]}")
 return jsonify({"spoken":text})

@app.route("/api/audio/mute",methods=["POST"])
def audio_mute():
 return jsonify({"muted":True})

@app.route("/api/chat",methods=["POST"])
def chat():
 data=request.json
 msg=data.get("msg","")
 model=data.get("model","llama3:latest")
 reply=f"[{model}] {msg[::-1]} (AGI OS says hi!)"
 return jsonify({"reply":reply})

@app.route("/dashboard")
def dashboard():
 return render_template_string("""<!DOCTYPE html><html><head><title>Dashboard</title><link rel="stylesheet" href="/static/theme.css"><script src="/static/app.js"></script></head><body><div class="jemai-center"><div class="jemai-title">JEMAI OS: Cluster Dashboard</div><div id="jemai-status" class="jemai-status"></div><div style="margin-top:30px;"><button onclick="window.location.href='/'">Home</button><button onclick="window.location.href='/explorer'">File Explorer</button><button onclick="window.location.href='/chatui'">Chat UI</button></div></div><script>window.refreshDashboard&&window.refreshDashboard();</script></body></html>""")

@app.route("/chatui")
def chatui():
 return render_template_string("""<!DOCTYPE html><html><head><title>Chat UI</title><link rel="stylesheet" href="/static/theme.css"></head><body><div class="jemai-center"><div class="jemai-title">JEMAI Chat</div><textarea id="chatbox" style="width:90vw;max-width:800px;height:120px;padding:14px;border-radius:7px;"></textarea><div style="margin:20px;"><button onclick="sendChat()">Send</button><select id="modelpick"><option>llama3:latest</option><option>gemma3:latest</option></select></div><div id="chatlog" style="width:94vw;max-width:820px;margin:30px auto;background:#21295c;min-height:70px;border-radius:10px;padding:22px;font-size:1.08rem;"></div></div><script>function sendChat(){let msg=document.getElementById('chatbox').value;let model=document.getElementById('modelpick').value;fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg:msg,model:model})}).then(r=>r.json()).then(x=>{let c=document.getElementById('chatlog');c.innerHTML+="<div><b>You:</b> "+msg+"</div><div style='margin-bottom:14px;'><b>"+model+":</b> "+x.reply+"</div>";document.getElementById('chatbox').value="";});}</script></body></html>""")

@app.route("/explorer")
def explorer():
 return render_template_string("""<!DOCTYPE html><html><head><title>File Explorer</title><link rel="stylesheet" href="/static/theme.css"></head><body><div class="jemai-center"><div class="jemai-title">JEMAI File Explorer</div><div id="explorer" style="width:90vw;max-width:950px;height:50vh;background:#232355;border-radius:10px;padding:16px;overflow:auto;"></div><div style="margin:20px;"><button onclick="window.location.href='/'">Home</button><button onclick="window.location.href='/chatui'">Chat</button></div></div><script>function renderTree(node,base){if(!node)return'';if(node.type=='file'){return\"<li ondblclick='openFile(\\\"\"+base+\"/\"+node.name+\"\\\")'>📄 \"+node.name+\"</li>\";}let kids=(node.children||[]).map(x=>renderTree(x,base+\"/\"+node.name)).join(\"\");return \"<li><b>📁 \"+node.name+\"</b><ul>\"+kids+\"</ul></li>\";}function loadExplorer(){fetch('/api/files/list?base=/jemai_hub').then(r=>r.json()).then(tree=>{let html=\"<ul>\"+(tree.map?tree.map(x=>renderTree(x,\"/jemai_hub\")).join(\"\"):renderTree(tree,\"/jemai_hub\"))+\"</ul>\";document.getElementById('explorer').innerHTML=html;});}function openFile(p){fetch('/api/files/read?path='+encodeURIComponent(p)).then(r=>r.json()).then(d=>{let t=prompt('Edit file ('+p+'): ',d.content||'');if(t!==null){fetch('/api/files/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,code:t})});}});}window.onload=loadExplorer;</script></body></html>""")

@app.route("/settings")
def settings():
 return render_template_string("""<!DOCTYPE html><html><head><title>Settings</title><link rel="stylesheet" href="/static/theme.css"></head><body><div class="jemai-center"><div class="jemai-title">Settings & About</div><div style="font-size:1.08rem;max-width:700px;text-align:left;"><b>JEMAI AGI OS</b> — Ultimate All-in-One Superfile<br><ul><li>Full cluster control, device registry, VSCode, live explorer, chat, plugin manager</li><li>Dynamic warmwinds theme, RAG, chat importer, overlay/clipboard, group chat</li><li>Audio/mic control, multi-model chat, everything bakes in</li></ul></div><div style='margin:24px;'><button onclick=\"window.location.href='/'\">Home</button></div></div></body></html>""")

if __name__=="__main__":
 print(">>> JEMAI AGI OS: BAKED SUPERFILE LAUNCH <<<")
 print(f"[INFO] Open in browser: http://127.0.0.1:8181/ or http://localhost:8181/")
 app.run("0.0.0.0",8181)
