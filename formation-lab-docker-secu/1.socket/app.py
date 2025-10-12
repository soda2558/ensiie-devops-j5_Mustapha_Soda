from flask import Flask, request, jsonify, render_template_string
import sys
import io

app = Flask(__name__)

# Template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Python Shell</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        textarea, input[type=text] { width: 100%; margin: 10px 0; padding: 10px; font-size: 14px; }
        button { padding: 10px 20px; font-size: 16px; }
        pre { background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>Python Shell</h1>
    <form method="POST" id="shellForm">
        <textarea name="command" rows="5" placeholder="Enter Python code here..."></textarea>
        <button type="submit">Run Code</button>
    </form>
    <h2>Output:</h2>
    <pre id="output">{{ output }}</pre>
</body>
</html>
"""

# Route to render the form and execute Python code
@app.route("/", methods=["GET", "POST"])
def shell():
    output = ""
    if request.method == "POST":
        code = request.form.get("command", "")
        output = execute_python_code(code)
    return render_template_string(HTML_TEMPLATE, output=output)


def execute_python_code(code):
    """Execute Python code and return the output."""
    # Capture the stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = sys.stdout

    try:
        exec(code, globals(), locals())
    except Exception as e:
        print(f"Error: {e}")

    # Get the output and reset stdout and stderr
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    return output


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
