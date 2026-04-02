import modal
import fastapi
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic_settings import BaseSettings, SettingsConfigDict


image = (
    modal.Image.debian_slim()
    .uv_sync()
    .env({"CONFIG_PATH_ENV_VAR": "/data/config.json"})
)

app = modal.App("eightctl-web", secrets=[
    modal.Secret.from_name("eightsleep-web"),
])
volume = modal.Volume.from_name(
    "eightctl-web-data",
    create_if_missing=True,
)


basic_http_bearer_dependency = Depends(HTTPBearer())


def authorize_token(
    token: HTTPAuthorizationCredentials = basic_http_bearer_dependency,
) -> bool:
    # TODO: rework this to get username/password from env vars and remove this comment. Also - I think we want the dependency to be like a cookie auth thing, not necessarily authorization: bearer. Not sure the right fastapi primitive for this. Figure it out and use it!
    if settings.GROUPTHERE_SOLVER_API_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API Error!",
        )
    if token.credentials != settings.GROUPTHERE_SOLVER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


webapp = fastapi.FastAPI(
    name="backend",
    dependencies=[
        Depends(authorize_token),
    ],
)


@app.function(image=image, volumes={"/data": volume})
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI, Request

    web_app = FastAPI()

    @web_app.post("/echo")
    async def echo(request: Request):
        body = await request.json()
        return body

    return web_app


@app.function(image=image, volumes={"/data": volume})
def list_files_in_volume():
    import os
    import datetime

    with open("/data/last_checked.txt", "w") as f:
        f.write(f"last checked: {datetime.datetime.now()}")
    files = os.listdir("/data")
    print("Files in volume:", files)
    volume.commit()


@app.local_entrypoint()
def main():
    list_files_in_volume.remote()
