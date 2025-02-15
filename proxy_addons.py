# repo: https://github.com/satomic/internal-proxy-for-copilot
# version: 1.2.0
# regular mode https://docs.mitmproxy.org/stable/concepts-modes/#regular-proxy
# mitmdump --listen-host 0.0.0.0 --listen-port 8080 --set block_global=false -s proxy_addons.py --mode regular
# upstream mode https://docs.mitmproxy.org/stable/concepts-modes/#upstream-proxy
# mitmdump --listen-host 0.0.0.0 --listen-port 8080 --set block_global=false -s proxy_addons.py --mode upstream:http://UPSTREAM_PROXY_IP:UPSTREAM_PROXY_PORT

import asyncio
from mitmproxy import http, ctx
import ipaddress
import re
from urllib.parse import urlparse


# Proxy switch
proxy_switch = True # True False

# Forbidden Note, you can change the note to your own note
forbidden_note = b"Your request is blocked, if you have any question, please contact YOUR_IT_ADMIN"

# Allow Personal Account
allow_personal_account = False
enterprise_slug = "fabrikam" # 🔥🔥🔥 change this to your real enterprise/standalone id
emu_enterpirse_sso_url = f"https://github.com/enterprises/{enterprise_slug}"
emu_enterprise_sso_login_note = f'<h1>Please login to {emu_enterpirse_sso_url}<br>Then try to login in your IDE.</h1>'

# Your allowed domains, you need to change the domain to your own domain, expecially change the `satomic` to your own organization name or enterprise name
your_allowed_domains = [
    # your enterprices related
    f"https://github.com/{enterprise_slug}/*",
    f"https://github.com/{enterprise_slug}?*",
    f"https://github.com/enterprises/{enterprise_slug}/*",
    f"https://github.com/login?return_to=https%3A%2F%2Fgithub.com%2Fenterprises%2F{enterprise_slug}",

    # anything you like
    # "https://www.google.com/*",
    # "https://www.baidu.com/*",
]

# GitHub Copilot official domains
# https://docs.github.com/en/copilot/managing-copilot/managing-github-copilot-in-your-organization/configuring-your-proxy-server-or-firewall-for-copilot
github_copilot_official_domains = [
    # "https://github.com/login?*",
    # "https://github.com/login/*",
    "https://github.com/login/oauth/*",
    "https://api.github.com/user/*",
    "https://api.github.com/copilot_internal/*",
    "https://copilot-telemetry.githubusercontent.com/telemetry/*",
    "https://default.exp-tas.com/*",
    "https://copilot-proxy.githubusercontent.com/*",
    "https://origin-tracker.githubusercontent.com/*",
    "https://*.githubcopilot.com/*",
    "https://*.individual.githubcopilot.com/*",
    "https://*.business.githubcopilot.com/*",
    "https://*.enterprise.githubcopilot.com/*",
]

github_public_domains = [
    # account
    "https://github.com/favicon.ico",
    "https://github.com/account/*",
    "https://github.com/settings/*",
    "https://avatars.githubusercontent.com/*",

    # docs
    "https://docs.github.com/*",
    
    # others
    "https://github.com/copilot/*",
    "https://raw.githubusercontent.com/*",
    "https://github.githubassets.com/*",
    "https://collector.github.com/*",
    "https://github.com/github-copilot/*",
    "https://collector.github.com/*",
    "https://api.github.com/*",
    "https://github.com/notifications/*",
    "https://github.com/session/*",
    "https://github.com/dashboard/*",
    "https://github.com/dashboard?*",

    # logout
    "https://github.com/logout/*",
    "https://github.com/logout?*",
    "https://github.com/",
    "https://github.com/switch_account?*",
    "https://github.com/switch_account/*",
]

# Microsoft Extra ID Domains and IPs
msft_extra_id_domains = [
    "https://login.microsoftonline.com/*",
    "https://aadcdn.msauth.net/*",
    "https://login.live.com/*",
    "https://*.activedirectory.windowsazure.com/*",
]

# IDE and extension domains
ide_extension_domains = [
    # VSCode
    "*visualstudio.com*",
    "*vscode-cdn*",
    "*vsassets.io*",
    "*gallerycdn.azure*",
    "*microsoft.com*",
    "*raw.githubusercontent.com*",
    "*digicert.com*",
    "https://vscode.dev/*",

    # JetBrains
    "*jetbrains.com*",
    "*jbstatic.com*",
]

# https://www.microsoft.com/en-us/download/details.aspx?id=56519 
msft_extra_id_ips = [
    "127.0.0.1",
    "4.149.98.192/27",
    "4.149.105.224/27",
    "4.150.253.96/28",
    "4.156.6.96/28",
    "4.190.147.80/28",
    "4.198.160.112/28",
    "4.207.244.176/28",
    "13.64.151.161/32",
    "13.66.141.64/27",
    "13.66.150.240/28",
    "13.67.9.224/27",
    "13.67.21.96/27",
    "13.69.66.160/27",
    "13.69.119.208/28",
    "13.69.229.96/27",
    "13.70.73.32/27",
    "13.71.172.160/27",
    "13.71.195.224/27",
    "13.71.201.64/26",
    "13.73.240.32/27",
    "13.74.104.0/26",
    "13.74.203.80/28",
    "13.74.249.156/32",
    "13.75.38.32/27",
    "13.75.105.168/32",
    "13.77.52.160/27",
    "13.78.108.192/27",
    "13.78.172.246/32",
    "13.79.37.247/32",
    "13.86.219.0/27",
    "13.87.16.0/26",
    "13.87.57.160/27",
    "13.87.123.160/27",
    "13.89.174.0/27",
    "20.18.183.32/28",
    "20.20.32.0/19",
    "20.36.107.192/27",
    "20.36.115.64/27",
    "20.36.151.160/28",
    "20.37.75.96/27",
    "20.40.228.64/28",
    "20.42.79.112/28",
    "20.43.120.32/27",
    "20.43.127.160/28",
    "20.44.3.160/27",
    "20.44.16.32/27",
    "20.46.10.64/27",
    "20.50.76.176/28",
    "20.50.206.128/28",
    "20.51.9.80/28",
    "20.51.14.72/31",
    "20.51.16.128/27",
    "20.61.98.160/27",
    "20.61.99.128/28",
    "20.62.58.80/28",
    "20.62.129.0/27",
    "20.62.129.240/28",
    "20.62.134.74/31",
    "20.65.4.192/28",
]



class ProxyOnlyForCopilot:
    
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        ctx.log.info("✅ Initialized ProxyReqRspSaveToJson plugin")

    def request(self, flow: http.HTTPFlow):
        
        request_url = flow.request.url
        client_ip = flow.client_conn.address[0]

        # Compatible with upstream mode, the situation that ip_address will be None
        ip_address = flow.server_conn.ip_address
        destination_ip = "0.0.0.0"
        if ip_address:
            destination_ip = flow.server_conn.ip_address[0]

        ctx.log.info(f"====================================================================================================")
        ctx.log.info(f"🔵 SRC IP: {client_ip}, DST IP: {destination_ip}, Request URL: {request_url}")

        def convert_pattern_to_regex(pattern):
            pattern = re.escape(pattern)
            pattern = pattern.replace(r'\*\.', '([^./]+\.)')
            pattern = pattern.replace(r'\*', '.*')
            pattern = f'^{pattern}$'
            
            return pattern

        def is_domain_allowed(request_url, allowed_domains):
            try:
                parsed = urlparse(request_url)
                if not all([parsed.scheme, parsed.netloc]):
                    return False
            except Exception:
                return False

            for pattern in allowed_domains:
                regex_pattern = convert_pattern_to_regex(pattern)
                if re.match(regex_pattern, request_url):
                    return True
                else:
                    if re.match(regex_pattern, request_url+"/"):
                        return True
            return False


        def is_ip_in_subnet(ip, subnet):
            try:
                ip = ipaddress.IPv4Address(ip)
                subnet = ipaddress.IPv4Network(subnet, strict=False)
                return ip in subnet
            except ValueError:
                return False

        def is_ip_allowed(destination_ip, allowed_ips):
            return any(is_ip_in_subnet(destination_ip, subnet) for subnet in allowed_ips)

        if proxy_switch:
            all_allowed_domains = your_allowed_domains + github_copilot_official_domains + github_public_domains + msft_extra_id_domains + ide_extension_domains
            if not is_domain_allowed(request_url, all_allowed_domains) and not is_ip_allowed(destination_ip, msft_extra_id_ips):
                ctx.log.info(f"❌ Request blocked")
                flow.response = http.Response.make(403, forbidden_note)
            else:
                # for webui copilot usage condition
                # if request_url == "https://github.com/" or "https://github.com/copilot" in request_url:
                #     cookies = dict(flow.request.cookies)
                #     dotcom_user = cookies.get('dotcom_user', '')
                #     logged_in = True if cookies.get('logged_in') == 'yes' else False

                if not allow_personal_account:
                    if "https://github.com/login?" in request_url:
                        flow.response = http.Response.make(403, emu_enterprise_sso_login_note)
                        ctx.log.info(f"🧭 Guide to Enterprise SSO")

                ctx.log.info(f"✅ Request allowed")


addons = [
    ProxyOnlyForCopilot()
]