"""CLI 入口 — 支持 stdio 和 HTTP 双传输模式."""

from __future__ import annotations

import logging
import sys

from googleplay_mcp.config import build_parser, load_config
from googleplay_mcp.server import create_server

logger = logging.getLogger("googleplay_mcp")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args)

    logger.info("transport=%s", config.server.transport)

    mcp = create_server(config)

    if config.server.transport == "http":
        logger.info("Starting HTTP server on %s:%s", config.server.host, config.server.port)
        mcp.run(
            transport="streamable-http",
            host=config.server.host,
            port=config.server.port,
        )
    else:
        logger.info("Starting stdio server")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
