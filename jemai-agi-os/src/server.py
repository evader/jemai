from flask import Flask, request
import json, os
app = Flask(__name__)
LOG_FILE = os.path.abspath('jemai_chat_log.jsonl')
@app.route('/new_reply', methods=['POST'])
def new_reply():
    data = request.json
    data['role'] = 'assistant'
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False)+'\n')
    return {'status':'ok'}
if __name__ == '__main__':
    app.run(port=8181)
