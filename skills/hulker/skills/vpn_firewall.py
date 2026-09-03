"""
vpn_firewall - VPN and firewall approval skill for Hulker.

Monitors VPN connection state, manages firewall rules for VPN applications,
and provides approval/denial for VPN traffic.

Invoke via voice: "HULKER skill vpn_firewall [command]"

Commands:
  status          — Show current VPN connections and firewall state
  list rules      — List all firewall rules related to VPN/software
  approve [app]   — Create/allow firewall rule for a VPN application
  deny [app]      — Block firewall rule for a VPN application
  enable profile  — Enable firewall profile (domain|private|public)
  disable profile — Disable firewall profile (domain|private|public)
  monitor [app]   — Start monitoring a VPN app's network activity
  check [host]    — Test if a host/port is reachable

Examples:
  "HULKER skill vpn_firewall status"
  "HULKER skill vpn_firewall approve NordVPN"
  "HULKER skill vpn_firewall deny Chrome"
  "HULKER skill vpn_firewall monitor tailscale"
"""

import sys
import subprocess
import ctypes
from typing import List, Optional, Tuple

# Windows API
user32 = ctypes.windll.user32
MANAGEMENT_FLAG = "powershell -ExecutionPolicy Bypass -Command"


def run_ps(cmd: str) -> Tuple[int, str, str]:
    """Run a PowerShell command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def get_vpn_connections() -> List[dict]:
    """Get all VPN connections configured on the system."""
    code = """
    $connections = Get-VpnConnection -ErrorAction SilentlyContinue | Select-Object Name, ConnectionStatus, ServerAddress, TunnelType
    if ($connections) {
        $connections | ConvertTo-Json -Depth 3
    } else {
        'null'
    }
    """
    rc, out, err = run_ps(code)
    if rc != 0 or out == "null" or not out:
        return []
    import json
    try:
        data = json.loads(out)
        if isinstance(data, list):
            return data
        return [data]
    except json.JSONDecodeError:
        return []


def get_firewall_profiles() -> dict:
    """Get firewall profile status (enabled/disabled per profile)."""
    code = """
    $profiles = Get-NetFirewallProfile | Select-Object Name, Enabled, LoggingEnabled
    $profiles | ConvertTo-Json -Depth 2
    """
    rc, out, err = run_ps(code)
    if rc != 0 or not out:
        return {}
    import json
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def get_firewall_rules(filter_str: str = "") -> List[dict]:
    """Get firewall rules, optionally filtered."""
    filter_part = f' -DisplayName "*{filter_str}*"' if filter_str else ""
    code = f"""
    $rules = Get-NetFirewallRule -Direction Inbound -Action Allow{filter_part} |
             Select-Object DisplayName, Enabled, Profile, Direction, Action, Description |
             ConvertTo-Json -Depth 2
    if ($rules) {{ $rules }} else {{ 'null' }}
    """
    rc, out, err = run_ps(code)
    if rc != 0 or out == "null" or not out:
        return []
    import json
    try:
        data = json.loads(out)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []


def createFirewallRule(name: str, app_path: str, action: str = "allow",
                       profiles: str = "any", description: str = ""):
    """Create a firewall rule for a VPN application."""
    action_ps = "Allow" if action.lower() == "allow" else "Block"
    profiles_ps = {
        "any": "Any",
        "domain": "Domain",
        "private": "Private",
        "public": "Public",
    }.get(profiles.lower(), "Any")

    desc = description or f"Hulker-managed {action} rule for {name}"

    code = f"""
    $existing = Get-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue
    if ($existing) {{
        Remove-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue
    }}
    New-NetFirewallRule `
        -DisplayName "{name}" `
        -Direction Inbound `
        -Action {action_ps} `
        -Program "{app_path}" `
        -Profile {profiles_ps} `
        -Description "{desc}" `
        -Enabled True
    """
    rc, out, err = run_ps(code)
    if rc == 0:
        return True, f"Firewall rule '{name}' created ({action} for {app_path})"
    return False, f"Failed to create rule: {err}"


def removeFirewallRule(name: str):
    """Remove a firewall rule by display name."""
    code = f"""
    $rule = Get-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue
    if ($rule) {{
        Remove-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue
        "Removed: {name}"
    }} else {{
        "Not found: {name}"
    }}
    """
    rc, out, err = run_ps(code)
    if rc == 0:
        return True, out or f"Rule '{name}' removed or not found."
    return False, err


def enableProfile(profile: str):
    """Enable a firewall profile."""
    code = f"Set-NetFirewallProfile -Name {profile} -Enabled True"
    rc, out, err = run_ps(code)
    if rc == 0:
        return True, f"Firewall profile '{profile}' enabled."
    return False, err


def disableProfile(profile: str):
    """Disable a firewall profile."""
    code = f"Set-NetFirewallProfile -Name {profile} -Enabled False"
    rc, out, err = run_ps(code)
    if rc == 0:
        return True, f"Firewall profile '{profile}' disabled."
    return False, err


def checkReachability(host: str, port: int = 443) -> bool:
    """Check if a host:port is reachable (TCP test)."""
    code = f"""
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {{
        $tcp.Connect("{host}", {port})
        $tcp.Close()
        "reachable"
    }} catch {{
        "unreachable"
    }}
    """
    rc, out, err = run_ps(code)
    return out.strip() == "reachable"


def findAppPath(app_name: str) -> Optional[str]:
    """Try to find the install path of an application by name."""
    code = f"""
    $apps = Get-ChildItem "C:\\Program Files", "C:\\Program Files (x86)" -Recurse -Filter "*.exe" -ErrorAction SilentlyContinue |
            Where-Object {{ $_.Name -like "*{app_name}*" }} |
            Select-Object -First 1 -ExpandProperty FullName
    if ($apps) {{ $apps }} else {{ "null" }}
    """
    rc, out, err = run_ps(code)
    if rc == 0 and out and out != "null":
        return out.strip()
    return None


def monitorApp(app_name: str):
    """Check if a VPN app process is running and report."""
    code = f"""
    $proc = Get-Process -Name "{app_name}" -ErrorAction SilentlyContinue
    if ($proc) {{
        $proc | Select-Object ProcessName, Id, CPU, WorkingSet, Path |
            ConvertTo-Json -Depth 2
    }} else {{
        "null"
    }}
    """
    rc, out, err = run_ps(code)
    if rc != 0 or out == "null" or not out:
        return None
    import json
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def status():
    """Print full VPN + firewall status."""
    print("=== VPN STATUS ===")
    vpns = get_vpn_connections()
    if vpns:
        for v in vpns:
            print(f"  {v.get('Name', '?')}: {v.get('ConnectionStatus', '?')} → {v.get('ServerAddress', '?')} ({v.get('TunnelType', '?')})")
    else:
        print("  No VPN connections configured.")

    print("\n=== FIREWALL PROFILES ===")
    profiles = get_firewall_profiles()
    if profiles:
        for p in profiles if isinstance(profiles, list) else [profiles]:
            print(f"  {p.get('Name', '?')}: Enabled={p.get('Enabled', '?')} Logging={p.get('LoggingEnabled', '?')}")
    else:
        print("  Unable to read firewall profiles.")

    print("\n=== RECENT FIREWALL RULES (VPN-related) ===")
    rules = get_firewall_rules("vpn")
    if rules:
        for r in rules if isinstance(rules, list) else [rules]:
            print(f"  {r.get('DisplayName', '?')} | {r.get('Action', '?')} | {r.get('Profile', '?')}")
    else:
        print("  No VPN-related firewall rules found.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "status":
        status()

    elif cmd == "list":
        filter_s = sys.argv[2] if len(sys.argv) > 2 else ""
        rules = get_firewall_rules(filter_s)
        if rules:
            print(f"Firewall rules (filter: '{filter_s}'):")
            for r in rules if isinstance(rules, list) else [rules]:
                print(f"  {r.get('DisplayName', '?')} | {r.get('Action', '?')} | {r.get('Profile', '?')} | {r.get('Enabled', '?')}")
        else:
            print("No matching firewall rules found.")

    elif cmd == "approve":
        if len(sys.argv) < 3:
            print("Usage: approve [app_name]")
            sys.exit(1)
        app = sys.argv[2]
        path = findAppPath(app)
        if not path:
            # Try common VPN paths
            common = {
                "nordvpn": "C:\\Program Files (x86)\\NordVPN\\NordVPN.exe",
                "nord": "C:\\Program Files (x86)\\NordVPN\\NordVPN.exe",
                "expressvpn": "C:\\Program Files\\ExpressVPN\\ExpressVPN.exe",
                "express": "C:\\Program Files\\ExpressVPN\\ExpressVPN.exe",
                "protonvpn": "C:\\Program Files\\Proton VPN\\protonvpn-cli.exe",
                "proton": "C:\\Program Files\\Proton VPN\\protonvpn-cli.exe",
                "mufasa": "C:\\Program Files\\Mullvad VPN\\mullvad.exe",
                "mullvad": "C:\\Program Files\\Mullvad VPN\\mullvad.exe",
                "tailscale": "C:\\Program Files\\Tailscale\\tailscaled.exe",
                "wireguard": "C:\\Program Files\\WireGuard\\WireGuard.exe",
                "surfshark": "C:\\Program Files\\Surfshark\\surfshark.exe",
                "cyberghost": "C:\\Program Files\\CyberGhost VPN\\CyberGhost.exe",
                "purevpn": "C:\\Program Files\\PureVPN\\PureVPN.exe",
                "hotspot": "C:\\Program Files\\Hotspot Shield\\hsssvc.exe",
                "hotspot shield": "C:\\Program Files\\Hotspot Shield\\hsssvc.exe",
            }
            path = common.get(app.lower())
        if not path:
            print(f"Could not find app path for '{app}'. Specify full path or install first.")
            sys.exit(1)
        rc, msg = createFirewallRule(f"Hulker-{app}-allow", path, action="allow")
        print(msg)

    elif cmd == "deny":
        if len(sys.argv) < 3:
            print("Usage: deny [app_name]")
            sys.exit(1)
        app = sys.argv[2]
        path = findAppPath(app)
        if not path:
            common = {
                "nordvpn": "C:\\Program Files (x86)\\NordVPN\\NordVPN.exe",
                "nord": "C:\\Program Files (x86)\\NordVPN\\NordVPN.exe",
                "expressvpn": "C:\\Program Files\\ExpressVPN\\ExpressVPN.exe",
                "express": "C:\\Program Files\\ExpressVPN\\ExpressVPN.exe",
                "protonvpn": "C:\\Program Files\\Proton VPN\\protonvpn-cli.exe",
                "proton": "C:\\Program Files\\Proton VPN\\protonvpn-cli.exe",
                "mullvad": "C:\\Program Files\\Mullvad VPN\\mullvad.exe",
                "mufasa": "C:\\Program Files\\Mullvad VPN\\mullvad.exe",
                "tailscale": "C:\\Program Files\\Tailscale\\tailscaled.exe",
                "wireguard": "C:\\Program Files\\WireGuard\\WireGuard.exe",
                "surfshark": "C:\\Program Files\\Surfshark\\surfshark.exe",
                "cyberghost": "C:\\Program Files\\CyberGhost VPN\\CyberGhost.exe",
                "purevpn": "C:\\Program Files\\PureVPN\\PureVPN.exe",
                "hotspot shield": "C:\\Program Files\\Hotspot Shield\\hsssvc.exe",
                "hotspot": "C:\\Program Files\\Hotspot Shield\\hsssvc.exe",
            }
            path = common.get(app.lower())
        if not path:
            print(f"Could not find app path for '{app}'. Specify full path.")
            sys.exit(1)
        rc, msg = createFirewallRule(f"Hulker-{app}-deny", path, action="block")
        print(msg)

    elif cmd == "enable":
        if len(sys.argv) < 3:
            print("Usage: enable [domain|private|public]")
            sys.exit(1)
        profile = sys.argv[2].lower()
        if profile not in ("domain", "private", "public"):
            print(f"Unknown profile: {profile}. Use domain, private, or public.")
            sys.exit(1)
        rc, msg = enableProfile(profile)
        print(msg)

    elif cmd == "disable":
        if len(sys.argv) < 3:
            print("Usage: disable [domain|private|public]")
            sys.exit(1)
        profile = sys.argv[2].lower()
        if profile not in ("domain", "private", "public"):
            print(f"Unknown profile: {profile}. Use domain, private, or public.")
            sys.exit(1)
        rc, msg = disableProfile(profile)
        print(msg)

    elif cmd == "monitor":
        if len(sys.argv) < 3:
            print("Usage: monitor [app_name]")
            sys.exit(1)
        app = sys.argv[2]
        result = monitorApp(app)
        if result:
            if isinstance(result, list):
                for p in result:
                    print(f"  {p.get('ProcessName', '?')} (PID {p.get('Id', '?')}) CPU: {p.get('CPU', '?')} MB Mem: {p.get('WorkingSet', '?')}")
            else:
                print(f"  {result.get('ProcessName', '?')} (PID {result.get('Id', '?')}) CPU: {result.get('CPU', '?')} MB Mem: {result.get('WorkingSet', '?')}")
        else:
            print(f"'{app}' is not running.")

    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: check [host] [port]")
            sys.exit(1)
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 443
        reachable = checkReachability(host, port)
        status_str = "REACHABLE" if reachable else "UNREACHABLE"
        print(f"{host}:{port} → {status_str}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
