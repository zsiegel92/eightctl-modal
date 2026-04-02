from __future__ import annotations

from modal import (
    App,
    Image,
    Secret,
    Volume,
    asgi_app,
    concurrent,
)

from eightctl_web.app import create_app

image = (
    Image.debian_slim()
    .add_local_dir("py-eightctl", remote_path="/.uv/py-eightctl", copy=True)
    .add_local_dir("src/eightctl_web", remote_path="/root/eightctl_web", copy=True)
    .uv_sync()
    .env({"PY_EIGHTCTL_CONFIG_PATH": "/data/py-eightctl-config.json"})
)

app = App(
    name="eightctl-web",
    image=image,
    secrets=[Secret.from_name("eightsleep-web")],
)
volume = Volume.from_name("eightctl-web-data", create_if_missing=True)


@app.function(volumes={"/data": volume})
@concurrent(max_inputs=100)
@asgi_app()
def fastapi_app():
    return create_app(commit_hook=volume.commit)


@app.function(volumes={"/data": volume})
def list_volume_files() -> list[str]:
    from pathlib import Path

    return sorted(path.name for path in Path("/data").iterdir())


@app.local_entrypoint()
def main() -> None:
    print(list_volume_files.remote())
