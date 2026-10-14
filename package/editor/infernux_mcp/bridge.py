"""Standard stdio MCP entry point; forwards to the authenticated Editor HTTP host."""

import argparse

from client import create_loopback_client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    args = parser.parse_args()
    from fastmcp.server import create_proxy

    proxy = create_proxy(create_loopback_client(args.endpoint), name="Infernux Editor")
    proxy.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
