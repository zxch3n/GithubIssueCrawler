# Github Issue Crawler


This repo supports:

- 🚃Crawling github issues
- 👖Finding all the related commits and PRs
- 🐮Get all the changed file for the commits and PRs.


Limited by the github api quota, we cannot crawl too fast. With multithread, the average speed is about 1~2 issues per second per account.

## Usage

1. Fill in your account information in the user.info.json file.
2. Set your target repo in the crawl.py
3. run `python crawl.py` 🚀
