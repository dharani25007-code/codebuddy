from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# -------- Coding Question Filter -------- #
def is_coding_question(question):
    coding_keywords = [
        "python", "java", "c++", "javascript", "html", "css",
        "react", "node", "api", "flask", "django",
        "error", "bug", "code", "program", "function",
        "loop", "array", "database", "sql", "algorithm",
        "class", "object", "variable", "compiler"
    ]
    question = question.lower()
    return any(keyword in question for keyword in coding_keywords)

# -------- Home Route -------- #
@app.route("/")
def home():
    return render_template("index.html")

# -------- Chat Route -------- #
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message")

        if not user_message:
            return jsonify({"reply": "No message received."})

        # Check coding related
        if not is_coding_question(user_message):
            return jsonify({
                "reply": "❌ I only answer programming and development questions."
            })

        # Check API key
        if not OPENROUTER_API_KEY:
            return jsonify({
                "reply": "❌ API key not found. Check your .env file."
            })

        # Send request to OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a strict coding assistant. Only answer programming questions."},
                    {"role": "user", "content": user_message}
                ]
            }
        )

        result = response.json()

        print("API RESPONSE:", result)  # Debug output

        # If API error
        if "choices" not in result:
            return jsonify({
                "reply": f"API Error: {result}"
            })

        return jsonify({
            "reply": result["choices"][0]["message"]["content"]
        })

    except Exception as e:
        print("SERVER ERROR:", str(e))
        return jsonify({
            "reply": f"Server Error: {str(e)}"
        })

# -------- Run Server -------- #
if __name__ == "__main__":
    app.run(debug=True)
