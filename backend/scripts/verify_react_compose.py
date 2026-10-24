"""Compatibility command for the authoritative complete-stack verification."""

import argparse

from verify_docker_startup import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--worker-image", default="scope-guard-worker:ci")
    args = parser.parse_args()
    print(
        verify(
            api_image=args.backend_image,
            frontend_image=args.frontend_image,
            worker_image=args.worker_image,
        )
    )


if __name__ == "__main__":
    main()
