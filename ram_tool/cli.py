#!/usr/bin/env python3
import argparse
import getpass
import hashlib
import json
import os
import sys
import time
from urllib.parse import urlencode
import requests

API = "https://jjjm03299-wq.github.io/solid-potato/api/get-ram/"
APP_DIR = os.path.join(os.path.expanduser("~"), ".ram-tool")
AUTH_FILE = os.path.join(APP_DIR, "auth.json")
SESSION_FILE = os.path.join(APP_DIR, "session.json")
SESSION_TIMEOUT = 180
VERSION = "1.0.5"


def ensure_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def sha256(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def register():
    if os.path.exists(AUTH_FILE):
        print("PIN already registered.")
        return
    pin1 = getpass.getpass("Enter new PIN: ")
    pin2 = getpass.getpass("Confirm new PIN: ")
    if pin1 != pin2:
        print("PINs do not match.")
        sys.exit(1)
    save(AUTH_FILE, {"hash": sha256(pin1)})
    print("PIN registered successfully.")


def login():
    auth = load(AUTH_FILE)
    if auth is None:
        print("No PIN registered.")
        return
    pin = getpass.getpass("Enter PIN: ")
    if sha256(pin) != auth["hash"]:
        print("Invalid PIN.")
        sys.exit(1)
    save(
        SESSION_FILE,
        {"expires": time.time() + SESSION_TIMEOUT},
    )
    print("Login successful.")


def logout():
    auth = load(AUTH_FILE)
    if auth is None:
        print("No PIN registered.")
        return
    pin = getpass.getpass("Enter PIN: ")
    if sha256(pin) != auth["hash"]:
        print("Invalid PIN.")
        sys.exit(1)
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("Logged out successfully.")


def auth_list():
    if not os.path.exists(AUTH_FILE):
        print("No PIN registered.")
        return

    print("--- Authentication Metadata ---")
    print(f"Auth file path: {AUTH_FILE}")
    print("Status: Registered")

    if os.path.exists(SESSION_FILE):
        session = load(SESSION_FILE)
        if session and time.time() <= session["expires"]:
            remaining = max(0, int(session["expires"] - time.time()))
            print(f"Session: Active (expires in {remaining}s)")
        else:
            print("Session: Expired")
    else:
        print("Session: Inactive / Logged out")


def auth_whoami():
    if not os.path.exists(AUTH_FILE):
        print("No PIN registered.")
        return

    if os.path.exists(SESSION_FILE):
        session = load(SESSION_FILE)
        if session and time.time() <= session["expires"]:
            remaining = max(0, int(session["expires"] - time.time()))
            print("Current status: Authenticated (Active Session)")
            print(f"Session expires in {remaining} seconds.")
            return

    print("Current status: Registered, but currently logged out or session expired.")


def auth_switch():
    auth = load(AUTH_FILE)
    if auth is None:
        print("No PIN registered. Please register first.")
        return

    print("--- Switch PIN Metadata ---")
    pin = getpass.getpass("Enter current PIN to verify: ")
    if sha256(pin) != auth["hash"]:
        print("Invalid PIN.")
        sys.exit(1)

    new_pin1 = getpass.getpass("Enter new PIN: ")
    new_pin2 = getpass.getpass("Confirm new PIN: ")
    if new_pin1 != new_pin2:
        print("PINs do not match.")
        sys.exit(1)

    save(AUTH_FILE, {"hash": sha256(new_pin1)})
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("PIN switched/updated successfully. Please log in again.")


def auth_remove():
    auth = load(AUTH_FILE)
    if auth is None:
        print("No PIN registered.")
        return

    pin = getpass.getpass("Enter pin to remove: ")
    if sha256(pin) != auth["hash"]:
        print("Invalid PIN.")
        sys.exit(1)

    confirm = input("Type REMOVE to continue: ")
    if confirm != "REMOVE":
        print("Confirmation failed. Aborted.")
        sys.exit(1)

    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("PIN and session removed successfully.")


def reset():
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("PIN reset successfully.")


def authenticated():
    session = load(SESSION_FILE)
    if session is None:
        print("❌ Access Denied: PIN session expired or locked.")
        print("Please authenticate using 'ram-tool auth login' first.")
        return False
    if time.time() > session["expires"]:
        os.remove(SESSION_FILE)
        print("❌ Access Denied: PIN session expired or locked.")
        print("Please authenticate using 'ram-tool auth login' first.")
        return False
    return True


def status():
    if not authenticated():
        return
    session = load(SESSION_FILE)
    remaining = max(0, int(session["expires"] - time.time()))
    print("Authenticated")
    print(f"Session expires in {remaining} seconds.")


def get_ram():
    if not authenticated():
        return
    try:
        response = requests.get(API, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "ram_mb" not in data:
            print("API error: 'ram_mb' not found.")
            sys.exit(1)
        print(f"RAM: {data['ram_mb']} MB")
    except requests.RequestException as e:
        print("API error:", e)
        sys.exit(1)
    except (ValueError, KeyError) as e:
        print("Invalid API response:", e)
        sys.exit(1)


def api_request(
    method,
    url,
    headers=None,
    data=None,
    files=None,
    auth=None,
):
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            files=files,
            auth=auth,
            timeout=30,
        )
        print(f"HTTP {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except ValueError:
            print(response.text)
    except requests.RequestException as e:
        print("API error:", e)
        sys.exit(1)


def api_command(args):
    method = args.method or args.X or "GET"
    headers = {}
    if args.headers:
        for header in args.headers:
            if ":" not in header:
                print(f"Invalid header: {header}")
                sys.exit(1)
            name, value = header.split(":", 1)
            headers[name.strip()] = value.strip()

    data = args.data
    if args.data_raw is not None:
        data = args.data_raw

    if args.data_urlencode:
        encoded_items = []
        for item in args.data_urlencode:
            if "=" in item:
                name, value = item.split("=", 1)
                encoded_items.append((name, value))
            else:
                encoded_items.append((item, ""))
        data = urlencode(encoded_items)

    if data and not any(
        key.lower() == "content-type" for key in headers
    ):
        headers["Content-Type"] = (
            "application/x-www-form-urlencoded"
        )

    files = None
    if args.form:
        files = {}
        for item in args.form:
            if "=" not in item:
                print(f"Invalid form field: {item}")
                sys.exit(1)
            name, value = item.split("=", 1)
            files[name] = (None, value)

    auth_tuple = None
    if args.user:
        if ":" in args.user:
            user, pwd = args.user.split(":", 1)
            auth_tuple = (user, pwd)
        else:
            auth_tuple = (args.user, "")

    api_request(
        method=method.upper(),
        url=args.url,
        headers=headers or None,
        data=data,
        files=files,
        auth=auth_tuple,
    )


def version():
    print(f"ram-tool {VERSION}")


def main():
    ensure_dir()
    parser = argparse.ArgumentParser(
        prog="ram-tool",
        description="Fetch RAM value from API",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}", help="Show version",
    )
    sub = parser.add_subparsers(
        dest="command",
        title="commands",
    )
    sub.add_parser(
        "get",
        help="Fetch RAM from API",
    )
    sub.add_parser(
        "get-ram",
        help="Fetch RAM from API (default GET)",
    )
    sub.add_parser(
        "version",
        help="Show version",
    )

    # -------------------------
    # AUTH
    # -------------------------
    auth = sub.add_parser(
        "auth",
        help="Authentication commands",
    )
    auth_sub = auth.add_subparsers(
        dest="action",
        title="auth commands",
    )
    auth_sub.add_parser(
        "register",
        help="Register a new PIN",
    )
    auth_sub.add_parser(
        "login",
        help="Login with PIN",
    )
    auth_sub.add_parser(
        "logout",
        help="Logout",
    )
    auth_sub.add_parser(
        "status",
        help="Show authentication status",
    )
    auth_sub.add_parser(
        "list",
        help="List pin metadata",
    )
    auth_sub.add_parser(
        "whoami",
        help="Show current auth identity/session state",
    )
    auth_sub.add_parser(
        "switch",
        help="Switch/change pin metadata",
    )
    auth_sub.add_parser(
        "remove",
        help="Remove pin session",
    )
    auth_sub.add_parser(
        "reset",
        help="Reset PIN and session",
    )

    # -------------------------
    # API
    # -------------------------
    api = sub.add_parser(
        "api",
        help="Make an HTTP API request",
    )
    api.add_argument(
        "--method",
        help="HTTP method, e.g. GET, POST, PUT, DELETE (default: GET)",
    )
    api.add_argument(
        "-X", dest="X", help="HTTP method alias",
    )
    api.add_argument(
        "-u", "--url", required=True, help="API URL",
    )
    api.add_argument(
        "-H", "--header", dest="headers", action="append", help="HTTP header",
    )
    api.add_argument(
        "-f", "--form", dest="form", action="append", help="Form field, e.g. -f 'name=value'",
    )
    api.add_argument(
        "-d", "--data", dest="data", help="Request body",
    )
    api.add_argument(
        "--data-raw", dest="data_raw", help="Raw request body data",
    )
    api.add_argument(
        "--data-urlencode", dest="data_urlencode", action="append", help="URL-encode request data",
    )
    api.add_argument(
        "--user", dest="user", help="HTTP Basic Auth user:password",
    )

    args = parser.parse_args()

    if args.command in ("get", "get-ram"):
        get_ram()
    elif args.command == "version":
        version()
    elif args.command == "auth":
        if args.action == "register":
            register()
        elif args.action == "login":
            login()
        elif args.action == "logout":
            logout()
        elif args.action == "status":
            status()
        elif args.action == "list":
            auth_list()
        elif args.action == "whoami":
            auth_whoami()
        elif args.action == "switch":
            auth_switch()
        elif args.action == "remove":
            auth_remove()
        elif args.action == "reset":
            reset()
        else:
            auth.print_help()
    elif args.command == "api":
        api_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
