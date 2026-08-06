from uvicorn.workers import UvicornWorker


class ProxyHeadersUvicornWorker(UvicornWorker):
    """Uvicorn worker that trusts X-Forwarded-* from the edge proxy (Caddy).

    Gunicorn does not accept uvicorn CLI flags like --proxy-headers /
    --forwarded-allow-ips; configure them via CONFIG_KWARGS instead.
    """

    CONFIG_KWARGS = {
        "loop": "auto",
        "http": "auto",
        "proxy_headers": True,
        "forwarded_allow_ips": "*",
    }
