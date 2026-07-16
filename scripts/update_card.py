#!/usr/bin/env python3
"""
Fetches live GitHub stats for a user and injects them into the SVG card
template, producing an up-to-date github_readme_card_text.svg.

Requires an environment variable GH_TOKEN (a GitHub token with at least
`read:user` scope) so the GraphQL contributions query works and so we
don't hit the low unauthenticated REST rate limit.
"""

import os
import sys
import datetime
import requests

USERNAME = "soumyacodr"
TOKEN = os.environ.get("GH_TOKEN")

if not TOKEN:
    sys.exit("ERROR: GH_TOKEN environment variable is not set.")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_profile_stats():
    """repos, followers, following via REST."""
    r = requests.get(f"https://api.github.com/users/{USERNAME}", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return {
        "repos": data["public_repos"],
        "followers": data["followers"],
        "following": data["following"],
    }


def get_total_stars():
    """Sum stargazers_count across all public repos (paginated)."""
    stars = 0
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner"},
        )
        r.raise_for_status()
        repos = r.json()
        if not repos:
            break
        stars += sum(repo["stargazers_count"] for repo in repos)
        page += 1
    return stars


def get_contributions_past_year():
    """Contributions in the last 365 days via the GraphQL API."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    r = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={"query": query, "variables": {"login": USERNAME}},
    )
    r.raise_for_status()
    data = r.json()
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"][
        "totalContributions"
    ]


def main():
    profile = get_profile_stats()
    stars = get_total_stars()
    contributions = get_contributions_past_year()

    with open("templates/card_template.svg", "r", encoding="utf-8") as f:
        svg = f.read()

    replacements = {
        "{{REPOS}}": str(profile["repos"]),
        "{{FOLLOWERS}}": str(profile["followers"]),
        "{{FOLLOWING}}": str(profile["following"]),
        "{{STARS}}": str(stars),
        "{{CONTRIBUTIONS}}": str(contributions),
        "{{TIMESTAMP}}": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    for placeholder, value in replacements.items():
        svg = svg.replace(placeholder, value)

    with open("github_readme_card_text.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print("Updated github_readme_card_text.svg with:", replacements)


if __name__ == "__main__":
    main()
