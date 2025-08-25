from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Auto Rename Bot is Running 🚀"
