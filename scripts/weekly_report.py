#!/usr/bin/env python3
"""Fetch the past week's GoatCounter stats and email a styled digest.

Required environment variables:
  GOATCOUNTER_CODE      site code, e.g. "soufianebouarfa" (subdomain of goatcounter.com)
  GOATCOUNTER_API_TOKEN GoatCounter API token with "read stats" permission
  RESEND_API_KEY        Resend API key (sending access)
  EMAIL_TO              recipient address (must match the Resend account's
                         verified email unless a custom domain is verified)
  EMAIL_FROM            optional, defaults to onboarding@resend.dev
"""
import datetime
import os

import requests

CODE = os.environ["GOATCOUNTER_CODE"]
TOKEN = os.environ["GOATCOUNTER_API_TOKEN"]
API = f"https://{CODE}.goatcounter.com/api/v0"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

NAVY = "#12233f"
GOLD = "#b08d57"
CREAM = "#faf6ee"
INK = "#1c2430"
MUTED = "#5c6472"
BORDER = "#e6ddc8"
GOOD = "#0ca30c"
BAD = "#d03b3b"

BAR_MAX_PX = 280


def iso(dt):
    return dt.strftime("%Y-%m-%dT00:00:00Z")


def week_ranges():
    today = datetime.datetime.utcnow().date()
    # most recent full Mon-Sun week that ended before today
    last_monday = today - datetime.timedelta(days=today.weekday() + 7)
    this_start = last_monday
    this_end = last_monday + datetime.timedelta(days=7)
    prev_start = last_monday - datetime.timedelta(days=7)
    prev_end = last_monday
    return this_start, this_end, prev_start, prev_end


def get(path, start, end, **params):
    r = requests.get(
        f"{API}/{path}",
        headers=HEADERS,
        params={"start": iso_date(start), "end": iso_date(end), **params},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def iso_date(d):
    return d.strftime("%Y-%m-%d")


def total_and_daily(start, end):
    data = get("stats/total", start, end)
    daily = [(day["day"], day["daily"]) for day in data["stats"]]
    return data["total"], daily


def top_list(page, start, end, limit=5):
    data = get(f"stats/{page}", start, end, limit=limit)
    key = "hits" if page == "hits" else "stats"
    return [(item.get("path") or item.get("name"), item["count"]) for item in data[key]]


def top_locations(start, end, limit=5):
    data = get("stats/locations", start, end, limit=limit)
    return [(item["name"], item["id"], item["count"]) for item in data["stats"]]


def top_shares(page, start, end, top_n=3):
    """Top N items plus each one's share of the (larger) sample fetched."""
    data = get(f"stats/{page}", start, end, limit=100)
    stats = data["stats"]
    sample_total = sum(item["count"] for item in stats)
    if sample_total == 0:
        return []
    return [
        (item["name"], round(item["count"] / sample_total * 100))
        for item in stats[:top_n]
    ]


def flag_emoji(country_code):
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in country_code.upper())


def delta_badge(current, previous):
    if previous == 0:
        return "", MUTED
    pct = round((current - previous) / previous * 100)
    if pct > 0:
        return f"&#9650; {pct}%", GOOD
    if pct < 0:
        return f"&#9660; {abs(pct)}%", BAD
    return "&#8212; 0%", MUTED


def bar_row(label, count, max_count, href=None):
    width = max(4, round(BAR_MAX_PX * count / max_count)) if max_count else 4
    label_html = f'<a href="{href}" style="color:{INK};text-decoration:none;">{label}</a>' if href else label
    return f"""
    <tr>
      <td style="padding:6px 0;font-size:13px;color:{INK};font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">
        {label_html}
        <div style="height:8px;border-radius:4px;background:{BORDER};width:{BAR_MAX_PX}px;margin-top:4px;">
          <div style="height:8px;border-radius:4px;background:{NAVY};width:{width}px;"></div>
        </div>
      </td>
      <td style="padding:6px 0 6px 12px;font-size:13px;color:{MUTED};text-align:right;vertical-align:top;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;white-space:nowrap;">
        {count}
      </td>
    </tr>"""


def sparkline_html(daily, max_height=32, bar_width=26):
    counts = [c for _, c in daily]
    max_c = max(counts) if counts and max(counts) > 0 else 1
    cells = []
    for i, (day, c) in enumerate(daily):
        h = max(3, round(max_height * c / max_c))
        color = NAVY if i == len(daily) - 1 else GOLD
        weekday = datetime.datetime.strptime(day[:10], "%Y-%m-%d").strftime("%a")[0]
        cells.append(f"""
        <td valign="bottom" style="padding:0 4px;text-align:center;">
          <div style="height:{h}px;width:{bar_width}px;background:{color};border-radius:3px 3px 0 0;"></div>
          <div style="font-size:9px;color:{MUTED};margin-top:3px;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">{weekday}</div>
        </td>""")
    return f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>{"".join(cells)}</tr></table>'


def chip_html(label, pct):
    return (
        f'<span style="display:inline-block;background:{CREAM};border:1px solid {BORDER};'
        f'border-radius:999px;padding:4px 10px;margin:0 6px 6px 0;font-size:12px;color:{INK};'
        f"font-family:system-ui,-apple-system,'Segoe UI',sans-serif;\">{label} "
        f'<span style="color:{GOLD};font-weight:600;">{pct}%</span></span>'
    )


def chips_section(title, items):
    if not items:
        chips = f'<span style="font-size:13px;color:{MUTED};">No data.</span>'
    else:
        chips = "".join(chip_html(name, pct) for name, pct in items)
    return f"""
    <tr>
      <td style="padding:28px 32px 8px 32px;">
        <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:{GOLD};font-weight:600;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">{title}</div>
        <div style="margin-top:10px;">{chips}</div>
      </td>
    </tr>"""


def section(title, rows, base_url=None):
    if not rows:
        rows_html = f'<tr><td style="padding:6px 0;font-size:13px;color:{MUTED};">No data.</td></tr>'
    else:
        max_count = max(c for _, c in rows)
        rows_html = "".join(
            bar_row(label, c, max_count, href=(base_url.rstrip("/") + label) if base_url else None)
            for label, c in rows
        )
    return f"""
    <tr>
      <td style="padding:28px 32px 8px 32px;">
        <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:{GOLD};font-weight:600;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">{title}</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
          {rows_html}
        </table>
      </td>
    </tr>"""


def build_email(
    site_url, start, end, total, prev_total, daily, pages, refs, locations, browsers, systems
):
    date_range = f"{start.strftime('%-d %b')} – {(end - datetime.timedelta(days=1)).strftime('%-d %b %Y')}"
    badge_text, badge_color = delta_badge(total, prev_total)
    flagged_locations = [(f"{flag_emoji(code)} {name}", count) for name, code, count in locations]

    return f"""\
<!doctype html>
<html>
<body style="margin:0;padding:0;background:{CREAM};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CREAM};padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid {BORDER};border-radius:8px;overflow:hidden;">
          <tr>
            <td style="background:{NAVY};padding:20px 32px;">
              <div style="color:#ffffff;font-size:15px;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-weight:600;">{site_url}</div>
              <div style="color:{GOLD};font-size:12px;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin-top:2px;">Weekly analytics &middot; {date_range}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 32px 8px 32px;">
              <div style="font-size:40px;line-height:1;font-weight:700;color:{INK};font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">{total}</div>
              <div style="font-size:13px;color:{MUTED};margin-top:4px;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">
                visits this week &middot; <span style="color:{badge_color};font-weight:600;">{badge_text}</span> vs previous week
              </div>
              <div style="margin-top:16px;">{sparkline_html(daily)}</div>
            </td>
          </tr>
          {section("Top pages", pages, base_url=f"https://{site_url}")}
          {section("Top referrers", refs)}
          {section("Top locations", flagged_locations)}
          {chips_section("Browsers", browsers)}
          {chips_section("Devices", systems)}
          <tr>
            <td style="padding:24px 32px 28px 32px;border-top:1px solid {BORDER};">
              <a href="https://{CODE}.goatcounter.com" style="color:{NAVY};font-size:13px;font-weight:600;text-decoration:none;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">View full dashboard &rarr;</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send(html, subject):
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
        json={
            "from": os.environ.get("EMAIL_FROM", "onboarding@resend.dev"),
            "to": [os.environ["EMAIL_TO"]],
            "subject": subject,
            "html": html,
        },
        timeout=30,
    )
    r.raise_for_status()


def main():
    this_start, this_end, prev_start, prev_end = week_ranges()

    total, daily = total_and_daily(this_start, this_end)
    prev_total, _ = total_and_daily(prev_start, prev_end)
    pages = top_list("hits", this_start, this_end)
    refs = top_list("toprefs", this_start, this_end)
    locations = top_locations(this_start, this_end)
    browsers = top_shares("browsers", this_start, this_end)
    systems = top_shares("systems", this_start, this_end)

    html = build_email(
        site_url=os.environ.get("SITE_URL", "your site"),
        start=this_start,
        end=this_end,
        total=total,
        prev_total=prev_total,
        daily=daily,
        pages=pages,
        refs=refs,
        locations=locations,
        browsers=browsers,
        systems=systems,
    )
    send(html, subject=f"Weekly analytics: {total} visits")


if __name__ == "__main__":
    main()
