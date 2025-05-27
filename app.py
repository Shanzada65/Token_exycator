from flask import Flask, request, jsonify, render_template
import re

app = Flask(__name__)

def extract_eaab_tokens(text):
    """Extracts EAAB tokens from a given text."""
    pattern = r'EAAB\w+'
    tokens = re.findall(pattern, text)
    valid_tokens = [token for token in tokens if 190 <= len(token) <= 200]
    return valid_tokens

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = request.form.get('data') or request.json.get('data')
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        tokens = extract_eaab_tokens(data)
        if tokens:
            return jsonify({"tokens": tokens})
        else:
            return jsonify({"error": "No valid EAAB tokens found"}), 404
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
