import random
import pandas as pd
from datetime import datetime, timedelta

categories = {
    "VPN": {
        "templates": [
            "Unable to connect to corporate VPN after password reset on {os}",
            "VPN login failing with error code {error} on {device}",
            "Frequent VPN disconnections while working from {location}",
            "MFA authentication failing during VPN login",
            "VPN access denied after recent security update"
        ],
        "resolution": "Clear cached VPN credentials, reauthenticate and verify MFA configuration"
    },

    "Login": {
        "templates": [
            "User account locked after multiple failed login attempts",
            "Forgot Windows system login password on {device}",
            "SSO authentication failing for internal portal",
            "Unable to login to domain after password expiration",
            "Active Directory sync issue preventing login"
        ],
        "resolution": "Reset password via admin console and unlock user account in Active Directory"
    },

    "WiFi": {
        "templates": [
            "Laptop not connecting to office WiFi network",
            "Intermittent WiFi disconnection on {os}",
            "Slow internet speed on corporate wireless network",
            "Unable to detect office SSID from {device}",
            "WiFi authentication failed due to security policy"
        ],
        "resolution": "Update network drivers, restart router and verify network security policies"
    },

    "Email": {
        "templates": [
            "Outlook application crashing on startup",
            "Unable to send emails via corporate Exchange server",
            "Emails stuck in outbox on {os}",
            "Shared mailbox not accessible in Outlook",
            "Microsoft Teams meeting invites not syncing"
        ],
        "resolution": "Reconfigure Outlook profile and resync with Exchange server"
    },

    "Access Control": {
        "templates": [
            "Access denied to shared network drive",
            "Permission error while accessing SharePoint site",
            "User unable to access HR portal",
            "File server access restricted unexpectedly",
            "Unauthorized access error in internal application"
        ],
        "resolution": "Grant appropriate permissions and verify role-based access control settings"
    }
}

oses = ["Windows 10", "Windows 11", "MacOS Ventura", "Ubuntu 22.04"]
devices = ["laptop", "desktop", "office workstation"]
locations = ["home network", "office network", "remote location"]
errors = ["720", "809", "691", "812"]

priorities = ["Low", "Medium", "High"]

data = []
ticket_id = 1

for category, details in categories.items():
    for _ in range(60):   # 60 tickets per category → total ~300
        template = random.choice(details["templates"])
        
        description = template.format(
            os=random.choice(oses),
            device=random.choice(devices),
            location=random.choice(locations),
            error=random.choice(errors)
        )
        
        data.append({
            "ticket_id": ticket_id,
            "description": description,
            "category": category,
            "priority": random.choice(priorities),
            "resolution": details["resolution"]
        })
        
        ticket_id += 1

df = pd.DataFrame(data)
df.to_csv("enterprise_synthetic_tickets.csv", index=False)

print("✅ Enterprise synthetic dataset generated successfully!")