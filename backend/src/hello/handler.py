import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HelloResponse:
    message: str


def make_hello_response() -> HelloResponse:
    return HelloResponse(message="hello from chai-s-romashkoi")


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    response = make_hello_response()
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(asdict(response)),
    }
