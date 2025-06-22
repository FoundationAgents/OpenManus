import tomllib
import webbrowser
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.route.tasks import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def format_validation_error(errors: list[Any]) -> Dict[str, Any]:
    """Format validation error messages"""
    formatted_errors = []
    for error in errors:
        loc = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        formatted_errors.append({"field": loc, "message": msg})
    return {
        "code": 400,
        "message": "Request parameter validation failed",
        "errors": formatted_errors,
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Handle request parameter validation errors"""
    return JSONResponse(status_code=400, content=format_validation_error(exc.errors()))


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(_: Request, exc: ValidationError):
    """Handle Pydantic model validation errors"""
    return JSONResponse(status_code=400, content=format_validation_error(exc.errors()))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    """Handle other exceptions"""
    return JSONResponse(
        status_code=500, content={"code": 500, "message": f"Server error: {str(exc)}"}
    )


def open_local_browser(config):
    webbrowser.open_new_tab(
        f"http://{config.get('host', 'localhost')}:{config.get('port', 5172)}"
    )


def load_config():
    try:
        config_path = Path(__file__).parent / "config" / "config.toml"

        if not config_path.exists():
            return {"host": "localhost", "port": 5172}

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        return {"host": config["server"]["host"], "port": config["server"]["port"]}
    except FileNotFoundError:
        return {"host": "localhost", "port": 5172}
    except KeyError as e:
        print(
            f"The configuration file is missing necessary fields: {str(e)}, use default configuration"
        )
        return {"host": "localhost", "port": 5172}


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    uvicorn.run(app, host=config["host"], port=config["port"])
