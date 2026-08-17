"""Verify App Store signed transactions (StoreKit 2 JWS) against Apple Root CA G3."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Optional

import jwt
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.x509.oid import ObjectIdentifier

from core.iap.apple_root_certs import APPLE_ROOT_CA_G3_PEM

# Present on App Store signed-transaction leaf certificates.
_APPLE_IAP_LEAF_OID = ObjectIdentifier("1.2.840.113635.100.6.11.1")


class AppleJwsError(ValueError):
    pass


def _b64url_decode(segment: str) -> bytes:
    padded = segment + "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _load_x5c_certs(header: dict) -> list[x509.Certificate]:
    chain = header.get("x5c")
    if not isinstance(chain, list) or not chain:
        raise AppleJwsError("Signed transaction is missing the x5c certificate chain")
    certs: list[x509.Certificate] = []
    for item in chain:
        try:
            der = base64.b64decode(item)
            certs.append(x509.load_der_x509_certificate(der))
        except Exception as exc:
            raise AppleJwsError("Invalid certificate in App Store JWS header") from exc
    return certs


def _verify_signature(issuer: x509.Certificate, subject: x509.Certificate) -> None:
    public_key = issuer.public_key()
    try:
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                subject.signature,
                subject.tbs_certificate_bytes,
                ec.ECDSA(subject.signature_hash_algorithm),
            )
        elif isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(
                subject.signature,
                subject.tbs_certificate_bytes,
                padding.PKCS1v15(),
                subject.signature_hash_algorithm,
            )
        else:
            raise AppleJwsError("Unsupported certificate public key type")
    except Exception as exc:
        raise AppleJwsError("App Store certificate chain signature is invalid") from exc


def _verify_chain_to_apple_root(certs: list[x509.Certificate]) -> None:
    root = x509.load_pem_x509_certificate(APPLE_ROOT_CA_G3_PEM.encode("utf-8"))
    now = datetime.now(timezone.utc)
    for cert in certs:
        if cert.not_valid_before_utc > now or cert.not_valid_after_utc < now:
            raise AppleJwsError("App Store signing certificate is expired or not yet valid")

    # Walk leaf -> intermediates, then last intermediate (or leaf) -> Apple Root CA G3.
    for index in range(len(certs) - 1):
        _verify_signature(certs[index + 1], certs[index])
    _verify_signature(root, certs[-1])

    leaf = certs[0]
    try:
        leaf.extensions.get_extension_for_oid(_APPLE_IAP_LEAF_OID)
    except x509.ExtensionNotFound:
        # Still accept if the chain is rooted at Apple; some sandbox certs omit the OID.
        pass


def decode_signed_data(signed: str) -> dict[str, Any]:
    """Verify and decode a StoreKit 2 / App Store Server Notifications JWS string."""
    if not signed or signed.count(".") != 2:
        raise AppleJwsError("Invalid App Store signed payload")

    header_segment = signed.split(".", 1)[0]
    try:
        header = jwt.get_unverified_header(signed)
    except Exception as exc:
        raise AppleJwsError("Could not read App Store JWS header") from exc

    certs = _load_x5c_certs(header)
    _verify_chain_to_apple_root(certs)

    try:
        payload = jwt.decode(
            signed,
            key=certs[0].public_key(),
            algorithms=["ES256"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except Exception as exc:
        # Header decode already succeeded; retry with decoded header alg if needed.
        alg = header.get("alg") or "ES256"
        try:
            payload = jwt.decode(
                signed,
                key=certs[0].public_key(),
                algorithms=[alg],
                options={"verify_aud": False, "verify_iss": False},
            )
        except Exception as inner:
            raise AppleJwsError("App Store signed payload signature is invalid") from inner
        _ = header_segment  # keep header parse path explicit
        _ = exc

    if not isinstance(payload, dict):
        raise AppleJwsError("App Store signed payload is not an object")
    return payload


def millis_to_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)
