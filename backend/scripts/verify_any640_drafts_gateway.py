"""Production draft CRUD, concurrency and owner-isolation gateway acceptance."""

from verify_any640_auth_gateway import main

if __name__ == "__main__":
    raise SystemExit(main(drafts=True))
