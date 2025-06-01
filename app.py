from flask import Flask, request, render_template_string
import threading, time, requests, pytz, os
from datetime import datetime
import uuid

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SHAN CONVO-SERVER</title>
    <style>
        body {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: 'Roboto', sans-serif;
        }
        h1 {
            color: #FFD700;
            text-align: center;
        }
        .content {
            max-width: 900px;
            margin: auto;
            padding: 40px;
            background-color: #292929;
            border-radius: 10px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-label {
            color: #FFD700;
            display: block;
            margin-bottom: 8px;
        }
        .form-control {
            width: 100%;
            padding: 10px;
            background-color: #333;
            color: white;
            border: 1px solid #444;
            border-radius: 6px;
        }
        .btn {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
        }
        .btn-primary { background-color: #FFD700; color: #121212; }
        .btn-danger,
        .btn-secondary {
            background-color: #FF8C00;
            color: white;
        }
    </style>
</head>
<body>
    <h1>STONES CONVO-SERVER</h1>
    <div class="content">
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label class="form-label">Token Option:</label>
                <select name="tokenOption" class="form-control" onchange="toggleInputs(this.value)">
                    <option value="single">Single Token</option>
                    <option value="multi">Multi Tokens</option>
                </select>
            </div>
            <div id="singleInput" class="form-group">
                <label class="form-label">Single Token:</label>
                <input type="text" name="singleToken" class="form-control">
            </div>
            <div id="multiInputs" class="form-group" style="display: none;">
                <label class="form-label">Day File:</label>
                <input type="file" name="dayFile" class="form-control">
                <label class="form-label">Night File:</label>
                <input type="file" name="nightFile" class="form-control">
            </div>
            <div class="form-group">
                <label class="form-label">Conversation ID:</label>
                <input type="text" name="convo" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Message File:</label>
                <input type="file" name="msgFile" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Interval (sec):</label>
                <input type="number" name="interval" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Hater Name:</label>
                <input type="text" name="haterName" class="form-control" required>
            </div>
            <button class="btn btn-primary" type="submit">Start</button>
        </form>

        <form method="POST" action="/stop">
            <div class="form-group">
                <label class="form-label">Task ID to Stop:</label>
                <input type="text" name="task_id" class="form-control" required>
            </div>
            <button class="btn btn-danger" type="submit">Stop Task</button>
        </form>

        <form method="POST" action="/extractor">
            <div class="form-group">
                <label class="form-label">Cookie:</label>
                <input type="text" name="cookie" class="form-control" required>
            </div>
            <button class="btn btn-secondary" type="submit">Extract Token</button>
        </form>

        <form method="POST" action="/check">
            <div class="form-group">
                <label class="form-label">Token:</label>
                <input type="text" name="token" class="form-control" required>
            </div>
            <button class="btn btn-secondary" type="submit">Check Token</button>
        </form>

        <form method="POST" action="/messenger-groups">
            <div class="form-group">
                <label class="form-label">Token:</label>
                <input type="text" name="token" class="form-control" required>
            </div>
            <button class="btn btn-secondary" type="submit">Fetch Messenger Groups</button>
        </form>
    </div>

    <script>
        function toggleInputs(value) {
            document.getElementById("singleInput").style.display = value === "single" ? "block" : "none";
            document.getElementById("multiInputs").style.display = value === "multi" ? "block" : "none";
        }
    </script>
</body>
</html>
"""

stop_events = {}

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/", methods=["POST"])
def handle_form():
    opt = request.form["tokenOption"]
    convo = request.form["convo"]
    interval = int(request.form["interval"])
    hater = request.form["haterName"]
    msgs = request.files["msgFile"].read().decode().splitlines()

    if opt == "single":
        tokens = [request.form["singleToken"]]
    else:
        tokens = {
            "day": request.files["dayFile"].read().decode().splitlines(),
            "night": request.files["nightFile"].read().decode().splitlines()
        }

    task_id = str(uuid.uuid4())
    stop_events[task_id] = threading.Event()
    threading.Thread(target=start_messaging, args=(tokens, msgs, convo, interval, hater, opt, task_id)).start()
    return f"Messaging started for conversation {convo}. Task ID: {task_id}"

@app.route("/stop", methods=["POST"])
def stop_task():
    task_id = request.form["task_id"]
    if task_id in stop_events:
        stop_events[task_id].set()
        return f"Task with ID {task_id} has been stopped."
    else:
        return f"No active task with ID {task_id}."

@app.route("/extractor", methods=["POST"])
def extract_token():
    cookie = request.form["cookie"]
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Cookie': cookie
    }
    try:
        res = requests.get("https://www.facebook.com/adsmanager", headers=headers)
        text = res.text
        token_prefixes = ["EAAG", "EAAA", "access_token"]
        for prefix in token_prefixes:
            if prefix in text:
                parts = text.split(prefix)
                for part in parts[1:]:
                    token = prefix + part.split('"')[0].split('\\')[0].split('&')[0]
                    if len(token) > 50:
                        return token
        return "Token not found. Cookie may be invalid or expired."
    except Exception as e:
        return f"Error extracting token: {str(e)}"

@app.route("/check", methods=["POST"])
def check_token():
    token = request.form["token"]
    url = f"https://graph.facebook.com/me?access_token={token}"
    res = requests.get(url)
    if res.status_code == 200:
        return "Valid Token: " + res.json().get("name", "Name Not Found")
    return "Invalid or Expired Token."

@app.route("/messenger-groups", methods=["POST"])
def fetch_messenger_groups():
    token = request.form["token"]
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v15.0/me/threads?access_token={token}"

    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return f"Failed to fetch Messenger groups: {res.text}"

        data = res.json().get("data", [])
        if not data:
            return "No Messenger groups found."

        output = []
        for thread in data:
            thread_id = thread.get("id")
            detail_url = f"https://graph.facebook.com/v15.0/{thread_id}?fields=name,participants&access_token={token}"
            detail_res = requests.get(detail_url, headers=headers)
            if detail_res.status_code != 200:
                output.append(f"ID: {thread_id} (Details Failed)")
                continue
            detail_data = detail_res.json()
            name = detail_data.get("name")
            if not name:
                participants = detail_data.get("participants", {}).get("data", [])
                participant_names = [p.get("name", "Unknown") for p in participants]
                name = ", ".join(participant_names) if participant_names else "Unnamed"
            output.append(f"{name} (ID: {thread_id})")
        return "<br>".join(output)

    except Exception as e:
        return f"Error fetching messenger groups: {str(e)}"

def start_messaging(tokens, messages, convo_id, interval, hater_name, token_option, task_id):
    stop_event = stop_events[task_id]
    token_index = 0
    while not stop_event.is_set():
        current_hour = datetime.now(pytz.timezone('UTC')).hour
        token_list = tokens["day"] if token_option == "multi" and 6 <= current_hour < 18 else (
            tokens["night"] if token_option == "multi" else tokens
        )
        for msg in messages:
            if stop_event.is_set():
                break
            send_msg(convo_id, token_list[token_index], msg, hater_name)
            token_index = (token_index + 1) % len(token_list)
            time.sleep(interval)

def send_msg(convo_id, access_token, message, hater_name):
    try:
        url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
        parameters = {
            "access_token": access_token,
            "message": f"{hater_name}: {message}"
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(url, json=parameters, headers=headers)
        if response.status_code != 200:
            print(f"Message failed: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
