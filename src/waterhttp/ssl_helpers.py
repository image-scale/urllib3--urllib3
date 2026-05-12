from __future__ import annotations

import hashlib
import hmac
import socket
import ssl
import typing

from .exceptions import SSLError


def create_ssl_context(
    ssl_minimum_version: int | None = None,
    ssl_maximum_version: int | None = None,
    cert_reqs: int | None = None,
    ciphers: str | None = None,
) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    context.check_hostname = False
    if cert_reqs is not None:
        context.verify_mode = ssl.VerifyMode(cert_reqs)
    else:
        context.verify_mode = ssl.CERT_REQUIRED

    if context.verify_mode == ssl.CERT_REQUIRED:
        context.check_hostname = True

    if ssl_minimum_version is not None:
        context.minimum_version = ssl.TLSVersion(ssl_minimum_version)
    else:
        context.minimum_version = ssl.TLSVersion.TLSv1_2

    if ssl_maximum_version is not None:
        context.maximum_version = ssl.TLSVersion(ssl_maximum_version)

    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_COMPRESSION

    if ciphers:
        context.set_ciphers(ciphers)

    try:
        context.set_alpn_protocols(["http/1.1"])
    except (AttributeError, NotImplementedError):
        pass

    return context


_HASHFUNC_MAP = {32: hashlib.md5, 40: hashlib.sha1, 64: hashlib.sha256}


def assert_fingerprint(cert: bytes | None, fingerprint: str) -> None:
    if cert is None:
        raise SSLError("No certificate for the peer.")

    fingerprint = fingerprint.replace(":", "").lower()
    digest_length = len(fingerprint)
    hashfunc = _HASHFUNC_MAP.get(digest_length)
    if not hashfunc:
        raise SSLError(f"Fingerprint of invalid length: {fingerprint}")

    cert_digest = hashfunc(cert).hexdigest()

    if not hmac.compare_digest(cert_digest.lower(), fingerprint.lower()):
        raise SSLError(
            f'Fingerprints did not match. Expected "{fingerprint}", '
            f'got "{cert_digest}"'
        )


def resolve_cert_reqs(candidate: int | str | None) -> int:
    if candidate is None:
        return ssl.CERT_REQUIRED

    if isinstance(candidate, str):
        candidate = candidate.upper()
        res_map = {
            "NONE": ssl.CERT_NONE,
            "CERT_NONE": ssl.CERT_NONE,
            "OPTIONAL": ssl.CERT_OPTIONAL,
            "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
            "REQUIRED": ssl.CERT_REQUIRED,
            "CERT_REQUIRED": ssl.CERT_REQUIRED,
        }
        return res_map.get(candidate, ssl.CERT_REQUIRED)

    return candidate


def ssl_wrap_socket(
    sock: socket.socket,
    keyfile: str | None = None,
    certfile: str | None = None,
    cert_reqs: int | None = None,
    ca_certs: str | None = None,
    server_hostname: str | None = None,
    ssl_context: ssl.SSLContext | None = None,
    ca_cert_dir: str | None = None,
    ca_cert_data: bytes | str | None = None,
) -> ssl.SSLSocket:
    context = ssl_context or create_ssl_context(cert_reqs=cert_reqs)

    if certfile:
        context.load_cert_chain(certfile, keyfile)

    if ca_certs or ca_cert_dir or ca_cert_data:
        try:
            context.load_verify_locations(ca_certs, ca_cert_dir, ca_cert_data)
        except OSError as e:
            raise SSLError(str(e)) from e
    elif context.verify_mode != ssl.CERT_NONE:
        context.load_default_certs()

    ssl_sock = context.wrap_socket(sock, server_hostname=server_hostname)
    return ssl_sock
