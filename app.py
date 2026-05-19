from flask import Flask, jsonify, render_template, request
import time
import os

app = Flask(__name__)

MAX_SAMPLES = 500

# ================= HISTORIAL =================

history = {

    "time": [],

    "voltaje": [],

    "corriente": []

}

# ================= PAGINA =================

@app.route("/")
def index():

    return render_template("index.html")

# ================= RECIBIR DATOS ESP32 =================

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

        voltaje = float(
            data.get("voltaje", 0)
        )

        corriente = float(
            data.get("corriente", 0)
        )

        # ===== GUARDAR DATOS =====

        history["time"].append(
            time.strftime("%H:%M:%S")
        )

        history["voltaje"].append(
            voltaje
        )

        history["corriente"].append(
            corriente
        )

        # ===== LIMITAR HISTORIAL =====

        for key in history:

            if len(history[key]) > MAX_SAMPLES:

                history[key].pop(0)

        print("Voltaje:", voltaje)
        print("Corriente:", corriente)

        return jsonify({

            "ok": True,

            "samples": len(
                history["voltaje"]
            )

        })

    except Exception as e:

        return jsonify({

            "ok": False,

            "error": str(e)

        }), 400

# ================= HISTORIAL =================

@app.route("/history")
def history_route():

    return jsonify(history)

# ================= STATUS =================

@app.route("/status")
def status():

    return jsonify({

        "ok": True,

        "samples":
        len(history["voltaje"])

    })

# ================= DEBUG =================

@app.route("/debug")
def debug():

    return jsonify({

        "samples":
        len(history["voltaje"]),

        "last_voltaje":
        history["voltaje"][-1]
        if history["voltaje"]
        else None,

        "last_corriente":
        history["corriente"][-1]
        if history["corriente"]
        else None

    })

# ================= MAIN =================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5050)
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
