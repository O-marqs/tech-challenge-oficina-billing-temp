"""Generate ephemeral local development keys; never replaces the real Auth issuer."""

import argparse
import base64
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", type=int, default=7)
    args = parser.parse_args()
    if args.client_id <= 0:
        parser.error("client-id must be positive")
    folder = Path(".local")
    folder.mkdir(exist_ok=True)
    # Every invocation creates an independent pair; no shared/checked-in private key.
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path = folder / "jwt-private.pem"
    with key_path.open("wb") as output:
        os.chmod(key_path, 0o600)
        output.write(
            private.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (folder / "jwt-public.b64").write_text(base64.b64encode(public).decode())
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "oficina-auth",
            "aud": "oficina-api",
            "sub": f"cliente:{args.client_id}",
            "cliente_id": args.client_id,
            "principal_type": "cliente",
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "jti": str(uuid4()),
        },
        private,
        algorithm="RS256",
    )
    token_path = folder / "client-token.txt"
    with token_path.open("w") as output:
        os.chmod(token_path, 0o600)
        output.write(token)
    print("Development public key: .local/jwt-public.b64; token: .local/client-token.txt (15 min).")
    print("Not an Auth integration test. Do not commit these files or use outside development.")


if __name__ == "__main__":
    main()
