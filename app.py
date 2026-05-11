from flask import Flask, jsonify, render_template, request
import time
import os

app = Flask(__name__)

MAX_SAMPLES = 50

# ---------------- DATA BUFFER ----------------
history = {
    "time": [],
    "adc1": [],
    "threshold": [],
    "pin23": []
}

# ---------------- MAIN PAGE ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- ESP32 POST DATA ----------------
@app.route("/data", methods=["POST"])
def recibir_data():

    global history

    data = request.get_json()

    if not data:
        return jsonify({
            "ok": False,
            "error": "No JSON recibido"
        }), 400

    try:

        adc1 = float(data.get("adc1", 0))
        threshold = float(data.get("threshold", 2.5))
        pin23 = int(data.get("pin23", 0))

        history["time"].append(time.strftime("%H:%M:%S"))
        history["adc1"].append(adc1)
        history["threshold"].append(threshold)
        history["pin23"].append(pin23)

        # limitar historial
        for key in history:
            if len(history[key]) > MAX_SAMPLES:
                history[key].pop(0)

        print("POST recibido:", data)

        return jsonify({
            "ok": True,
            "samples": len(history["adc1"])
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

# ---------------- FETCH HISTORY ----------------
@app.route("/history")
def history_route():
    return jsonify(history)

# ---------------- DEBUG ----------------
@app.route("/debug")
def debug():
    return jsonify({
        "samples": len(history["adc1"]),
        "last_adc": history["adc1"][-1] if history["adc1"] else None,
        "history": history
    })

# ---------------- STATUS ----------------
@app.route("/status")
def status():
    return jsonify({
        "ok": True,
        "mode": "HTTP POST",
        "samples": len(history["adc1"])
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5050))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )