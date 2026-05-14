from flask import Flask, jsonify, render_template, request
import time
import os

app = Flask(__name__)

MAX_SAMPLES = 50

# ---------------- VARIABLES ----------------
pwm_value = 0
threshold_value = 2.5

# ---------------- DATA BUFFER ----------------
history = {

    "time": [],

    "adc1": [],

    "threshold": [],

    "pin23": [],

    "boton": []
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

        adc1 = float(
            data.get("adc1", 0)
        )

        pin23 = int(
            data.get("pin23", 0)
        )

        boton = int(
            data.get("boton", 0)
        )

        history["time"].append(
            time.strftime("%H:%M:%S")
        )

        history["adc1"].append(adc1)

        history["threshold"].append(
            threshold_value
        )

        history["pin23"].append(pin23)

        history["boton"].append(boton)

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

# ---------------- PWM ----------------
@app.route("/pwm", methods=["GET", "POST"])
def pwm():

    global pwm_value

    if request.method == "POST":

        data = request.get_json()

        pwm_value = int(
            data.get("pwm", 0)
        )

        print("PWM:", pwm_value)

        return jsonify({

            "ok": True,

            "pwm": pwm_value
        })

    return jsonify({

        "pwm": pwm_value
    })

# ---------------- THRESHOLD ----------------
@app.route("/threshold", methods=["GET", "POST"])
def threshold():

    global threshold_value

    if request.method == "POST":

        data = request.get_json()

        threshold_value = float(
            data.get("threshold", 2.5)
        )

        print(
            "Threshold:",
            threshold_value
        )

        return jsonify({

            "ok": True,

            "threshold": threshold_value
        })

    return jsonify({

        "threshold": threshold_value
    })

# ---------------- DEBUG ----------------
@app.route("/debug")
def debug():

    return jsonify({

        "samples":
        len(history["adc1"]),

        "last_adc":
        history["adc1"][-1]
        if history["adc1"]
        else None,

        "history":
        history,

        "pwm":
        pwm_value,

        "threshold":
        threshold_value
    })

# ---------------- STATUS ----------------
@app.route("/status")
def status():

    return jsonify({

        "ok": True,

        "mode": "HTTP POST",

        "samples":
        len(history["adc1"])
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5050)
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False
    )
