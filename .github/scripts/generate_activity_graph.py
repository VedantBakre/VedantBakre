#!/usr/bin/env python3
"""
Generate GitHub Readme Activity Graph SVG
Custom generator for VedantBakre
"""

import os
import sys
import json
import math
import re
import urllib.request
from datetime import datetime

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER") or "VedantBakre"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("TOKEN")
OUTPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "activity-graph-output/activity-graph.svg"

# Theme colors (Tokyo-Night Purple/Pink configuration)
COLOR_TEXT = "70a5fd"
COLOR_TITLE = "70a5fd"
COLOR_LINE = "a855f7"
COLOR_POINT = "ec4899"
COLOR_AREA = "a855f7"
BG_COLOR = "00000000"

def fetch_contributions_graphql(username, token):
    url = "https://api.github.com/graphql"
    query = """
    query ($login: String!) {
      user(login: $login) {
        name
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    data = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        res_data = json.loads(res.read().decode("utf-8"))
    
    calendar = res_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    name = res_data["data"]["user"].get("name") or username
    days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({"date": day["date"], "count": day["contributionCount"]})
    return name, days

def fetch_contributions_scrape(username):
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as res:
        html = res.read().decode("utf-8")
    
    days = {}
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})" id="([^"]+)"', html):
        date, cid = m.group(1), m.group(2)
        days[cid] = {"date": date, "count": 0}
    
    for m in re.finditer(r'for="([^"]+)"[^>]*>([^<]+)</tool-tip>', html):
        cid, text = m.group(1), m.group(2)
        if cid in days:
            cnt_match = re.search(r'(\d+)\s+contribution', text)
            if cnt_match:
                days[cid]["count"] = int(cnt_match.group(1))
            elif "No contributions" in text:
                days[cid]["count"] = 0
                
    sorted_days = sorted(days.values(), key=lambda x: x["date"])
    name = "Vedant Bakre"
    return name, sorted_days

def smooth_path(pts, tension=0.25):
    if len(pts) < 2:
        return ""
    d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        
        cp1x = p1[0] + (p2[0] - p0[0]) * tension
        cp1y = p1[1] + (p2[1] - p0[1]) * tension
        cp2x = p2[0] - (p3[0] - p1[0]) * tension
        cp2y = p2[1] - (p3[1] - p1[1]) * tension
        
        d.append(f"C {cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(d)

def generate_svg(name, days_data):
    # Take the last 31 days
    last_31 = days_data[-31:]
    
    width = 1200
    height = 420
    pad_top = 80
    pad_bottom = 50
    pad_left = 75
    pad_right = 50
    
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    
    counts = [d["count"] for d in last_31]
    max_val = max(counts) if counts else 1
    if max_val <= 0:
        max_val = 4
    
    # Calculate Y-axis intervals
    num_y_ticks = 4
    step = max(1, math.ceil(max_val / num_y_ticks))
    y_max = step * num_y_ticks
    
    n_days = len(last_31)
    pts = []
    for i, d in enumerate(last_31):
        x = pad_left + (i * plot_w / (n_days - 1))
        # Y is inverted (0 at bottom)
        y = pad_top + plot_h - ((d["count"] / y_max) * plot_h)
        pts.append((x, y))
    
    line_d = smooth_path(pts)
    
    # Area path
    area_d = f"M {pts[0][0]:.1f} {pad_top + plot_h:.1f} L {pts[0][0]:.1f} {pts[0][1]:.1f} " + line_d[len(f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "):] + f" L {pts[-1][0]:.1f} {pad_top + plot_h:.1f} Z"
    
    # Horizontal grid lines and Y-axis labels
    grid_lines = []
    y_labels = []
    for t in range(num_y_ticks + 1):
        val = t * step
        y_pos = pad_top + plot_h - ((val / y_max) * plot_h)
        grid_lines.append(
            f'<line class="ct-grid" x1="{pad_left}" y1="{y_pos:.1f}" x2="{pad_left + plot_w}" y2="{y_pos:.1f}" />'
        )
        y_labels.append(
            f'<text class="ct-label" x="{pad_left - 15}" y="{y_pos + 4:.1f}" text-anchor="end">{val}</text>'
        )
    
    # Y-axis title
    y_title = f'<text class="ct-axis-title" transform="rotate(-90)" x="{- (pad_top + plot_h / 2):.1f}" y="25" text-anchor="middle">Contributions</text>'
    
    # X-axis grid lines and labels (show every ~4 days to prevent clutter)
    x_labels = []
    x_grid = []
    label_step = max(1, n_days // 8)
    for i, d in enumerate(last_31):
        x = pts[i][0]
        # Light vertical grid for all days
        x_grid.append(
            f'<line class="ct-grid" x1="{x:.1f}" y1="{pad_top}" x2="{x:.1f}" y2="{pad_top + plot_h}" />'
        )
        # Show label at intervals and at the last day
        if i % label_step == 0 or i == n_days - 1:
            try:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                label_str = dt.strftime("%b %d")
            except Exception:
                label_str = d["date"]
            x_labels.append(
                f'<text class="ct-label" x="{x:.1f}" y="{pad_top + plot_h + 24}" text-anchor="middle">{label_str}</text>'
            )
            
    # X-axis title
    x_title = f'<text class="ct-axis-title" x="{pad_left + plot_w / 2:.1f}" y="{height - 10}" text-anchor="middle">Days</text>'
    
    # Points
    points_svg = []
    for (x, y), d in zip(pts, last_31):
        points_svg.append(
            f'<line class="ct-point" x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y:.1f}"><title>{d["count"]} contributions on {d["date"]}</title></line>'
        )
        
    title_text = f"{name}'s Contribution Graph"
    
    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect data-testid="card_bg" id="cardBg" x="0" y="0" rx="15" height="100%" width="100%" fill="#{BG_COLOR}" stroke="#0000" style="stroke-width:0;"/>
  <style>
    body {{
      font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
    }}
    .header {{
      font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif;
      text-align: center;
      color: #{COLOR_TITLE};
      margin-top: 18px;
    }}
    svg {{
      font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
      user-select: none;
    }}
    .ct-label {{
      fill: #{COLOR_TEXT};
      color: #{COLOR_TEXT};
      font-size: 12px;
      font-family: 'Segoe UI', Ubuntu, Sans-Serif;
      font-weight: 500;
    }}
    .ct-axis-title {{
      fill: #{COLOR_TEXT};
      color: #{COLOR_TEXT};
      font-size: 13px;
      font-family: 'Segoe UI', Ubuntu, Sans-Serif;
      font-weight: 600;
      opacity: 0.85;
    }}
    .ct-grid {{
      stroke: #{COLOR_TEXT};
      stroke-width: 1px;
      stroke-opacity: 0.18;
      stroke-dasharray: 2.5px;
    }}
    .ct-area {{
      fill: #{COLOR_AREA};
      fill-opacity: 0.12;
      stroke: none;
    }}
    .ct-line {{
      fill: none;
      stroke-width: 3.5px;
      stroke-dasharray: 6000;
      stroke-dashoffset: 6000;
      stroke: #{COLOR_LINE};
      animation: dash 3.5s ease-in-out forwards;
    }}
    .ct-point {{
      stroke-width: 8.5px;
      stroke-linecap: round;
      stroke: #{COLOR_POINT};
      animation: blink 1s ease-in-out forwards;
      cursor: pointer;
    }}
    @keyframes blink {{
      from {{
        opacity: 0;
        transform: translateY(6px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}
    @keyframes dash {{
      to {{
        stroke-dashoffset: 0;
      }}
    }}
  </style>

  <foreignObject x="0" y="0" width="{width}" height="55">
    <h1 xmlns="http://www.w3.org/1999/xhtml" class="header">
      {title_text}
    </h1>
  </foreignObject>

  <!-- Grids -->
  <g class="ct-grids">
    {"".join(grid_lines)}
    {"".join(x_grid)}
  </g>

  <!-- Labels -->
  <g class="ct-labels">
    {"".join(y_labels)}
    {"".join(x_labels)}
    {y_title}
    {x_title}
  </g>

  <!-- Area Fill -->
  <path class="ct-area" d="{area_d}" />

  <!-- Smooth Line -->
  <path class="ct-line" d="{line_d}" />

  <!-- Points -->
  <g class="ct-points">
    {"".join(points_svg)}
  </g>
</svg>
"""
    return svg

def main():
    print(f"Generating Activity Graph for {USERNAME}...")
    name = "Vedant Bakre"
    days = None
    
    if TOKEN:
        try:
            print("Fetching via GitHub GraphQL API...")
            name, days = fetch_contributions_graphql(USERNAME, TOKEN)
            print(f"Fetched {len(days)} days via GraphQL.")
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Falling back to scraping...")
            
    if not days:
        print("Fetching via public contributions page...")
        name, days = fetch_contributions_scrape(USERNAME)
        print(f"Fetched {len(days)} days via scrape.")
        
    svg_content = generate_svg(name, days)
    
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"Activity Graph successfully written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
