import os
import logging
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_URL = "https://worldpanel24.com/api/v2"
MARKUP_PER_1K = 50


def get_world_panel_data(action):
    api_key = os.environ.get("WORLD_PANEL_API_KEY")

    if not api_key:
        raise RuntimeError("Supplier API key is not configured")

    response = requests.post(
        API_URL,
        json={
            "key": api_key,
            "action": action
        },
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError("Supplier API returned an error")

    return data


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "agency": "AM Panel Agency",
        "message": "API is running"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "status": "online"
    })


@app.route("/services", methods=["GET"])
def services():
    try:
        exchange_rate = float(os.environ["USD_TO_PKR"])

        if exchange_rate <= 0:
            raise ValueError("Invalid exchange rate")

        supplier_services = get_world_panel_data("services")

        if not isinstance(supplier_services, list):
            raise ValueError("Invalid services response")

        services_list = []

        for item in supplier_services:
            supplier_rate = float(item["rate"])

            # Supplier rate is per 1K.
            # Convert USD to PKR and add Rs. 50 markup.
            customer_rate = round(
                supplier_rate * exchange_rate + MARKUP_PER_1K,
                2
            )

            services_list.append({
                "service": item.get("service"),
                "name": item.get("name"),
                "type": item.get("type"),
                "category": item.get("category"),
                "rate": customer_rate,
                "min": item.get("min"),
                "max": item.get("max"),
                "currency": "PKR"
            })

        return jsonify({
            "success": True,
            "agency": "AM Panel Agency",
            "currency": "PKR",
            "markup_per_1k": MARKUP_PER_1K,
            "total_services": len(services_list),
            "services": services_list
        })

    except Exception:
        app.logger.exception("Could not load supplier services")

        return jsonify({
            "success": False,
            "error": "Unable to load services. Please try again."
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
      )
