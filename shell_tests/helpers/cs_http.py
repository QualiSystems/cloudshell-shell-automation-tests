import base64
from typing import Generator, Tuple

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from shell_tests.configs import CloudShellConfig


def get_reservation_errors(
    conf: CloudShellConfig, reservation_id: str
) -> Generator[Tuple[str, str], None, None]:
    """Get error messages from activity tab in reservation."""
    url = f"http://{conf.host}/"
    workspace_api = f"{url}api/WorkspaceApi/"
    login_url = f"{url}Account/Login"
    get_activities_url = (
        f"{workspace_api}GetFilteredActivityFeedInfoList?diagramId={reservation_id}"
    )
    public_key_url = f"{url}Account/PublicKey"
    get_activity_url = f"{workspace_api}GetActivityFeedInfo?eventId="
    data = {
        "FromEventId": 0,
        "IsError": True,
    }

    with requests.session() as session:
        resp = session.get(public_key_url)  # download public key
        public_key = serialization.load_pem_public_key(resp.content, default_backend())

        enc_user = public_key.encrypt(conf.user.encode(), padding.PKCS1v15())
        enc_user = base64.b64encode(enc_user)
        enc_pass = public_key.encrypt(conf.password.encode(), padding.PKCS1v15())
        enc_pass = base64.b64encode(enc_pass)

        session.post(login_url, data={"username": enc_user, "password": enc_pass})
        resp = session.post(get_activities_url, data=data)

        for id_ in [item["Id"] for item in resp.json()["Data"]["Items"]]:
            url = get_activity_url + str(id_)
            resp = session.get(url)
            data = resp.json()["Data"]
            text = data["Text"]
            output = data["Output"]

            yield text, output
