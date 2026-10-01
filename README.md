# RAM Tool (`ram-tool`)

A secure, feature-rich command-line interface (CLI) tool to fetch RAM data from an API and manage custom authenticated HTTP requests.

## Features

- **Secure PIN Authentication**: Encrypts and stores local PIN configurations (`.ram-tool/auth.json` and session state).
- **RAM Fetching**: Easily query server RAM metrics with built-in session enforcement.
- **Advanced API Client**: Make custom HTTP requests (GET, POST, PUT, DELETE) with support for headers, form fields, raw data, URL encoding, and HTTP Basic Authentication.
- **Session Management**: Built-in login, logout, status checks, whoami identity checks, and secure PIN removal/switching.

---

## Installation

You can install the tool directly from PyPI (once published) or via source:

```bash
pip install ram-tool
