import json
import re
from decimal import Decimal, DivisionByZero, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NUMBER_PATTERN = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)\Z")
OPERATIONS = {
    "add": lambda left, right: left + right,
    "subtract": lambda left, right: left - right,
    "multiply": lambda left, right: left * right,
    "divide": lambda left, right: left / right,
}


def calculate(left_text: str, right_text: str, operation: str) -> str:
    """Validate and calculate two decimal numbers."""
    if operation not in OPERATIONS:
        raise ValueError("Choose a valid operation.")

    values = []
    for text in (left_text, right_text):
        if not isinstance(text, str) or len(text) > 50 or not NUMBER_PATTERN.fullmatch(text):
            raise ValueError("Enter valid numbers.")
        try:
            values.append(Decimal(text))
        except InvalidOperation as error:
            raise ValueError("Enter valid numbers.") from error

    try:
        result = OPERATIONS[operation](*values)
    except DivisionByZero as error:
        raise ValueError("Cannot divide by zero.") from error

    if not result.is_finite():
        raise ValueError("The result is too large.")
    if result == 0:
        return "0"

    formatted = format(result, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


class CalculatorHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404, "Not found")
            return

        page = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self) -> None:
        if self.path != "/calculate":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024:
                raise ValueError("Invalid request.")
            payload = json.loads(self.rfile.read(length))
            result = calculate(
                payload.get("left"),
                payload.get("right"),
                payload.get("operation"),
            )
            response = {"result": result}
            status = 200
        except (ValueError, json.JSONDecodeError) as error:
            response = {"error": str(error)}
            status = 400
        except (TypeError, AttributeError):
            response = {"error": "Invalid request."}
            status = 400

        body = json.dumps(response).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), CalculatorHandler)
    print("Calculator running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down calculator.")
    finally:
        server.server_close()
