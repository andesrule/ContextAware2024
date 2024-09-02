from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test')
def api_test():
    return jsonify({"message": "API is working!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
