"""
Flask integration example for SimpleLogs
"""

from flask import Flask, request, g
from simplelogs import SimpleLogger

app = Flask(__name__)

# Initialize the logger
logger = SimpleLogger(
    base_url="http://localhost",
    api_key="YOUR_API_KEY",
    source="flask-app",
)


@app.before_request
def log_request():
    """Log every incoming request."""
    logger.info(f"{request.method} {request.path}", {
        "method": request.method,
        "path": request.path,
        "ip": request.remote_addr,
        "user_agent": request.user_agent.string,
    })


@app.errorhandler(Exception)
def handle_error(error):
    """Log all unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(error)}", {
        "path": request.path,
        "method": request.method,
        "error_type": type(error).__name__,
    })
    return {"error": "Internal server error"}, 500


@app.route("/")
def index():
    return {"message": "Hello, World!"}


@app.route("/users/<int:user_id>")
def get_user(user_id: int):
    logger.debug(f"Fetching user {user_id}", {"user_id": user_id})

    # Simulate user lookup
    user = {"id": user_id, "name": "John Doe"}

    logger.info(f"User {user_id} retrieved", {"user_id": user_id})
    return user


@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json()

    logger.info("Checkout started", {
        "user_id": data.get("user_id"),
        "cart_total": data.get("total"),
    })

    # Simulate payment processing
    success = True

    if success:
        logger.info("Payment successful", {
            "user_id": data.get("user_id"),
            "amount": data.get("total"),
        })
        return {"status": "success"}
    else:
        logger.error("Payment failed", {
            "user_id": data.get("user_id"),
            "amount": data.get("total"),
            "reason": "Card declined",
        })
        return {"status": "failed"}, 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
