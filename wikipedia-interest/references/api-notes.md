# API Notes for Wikimedia APIs

This document summarizes the observed behavior of the Wikimedia APIs used in the wikipedia-interest skill, based on live calls made during reconnaissance.

## User-Agent
All requests must include a descriptive User-Agent header with contact information. The contact information should be taken from the environment variable `WIKITRENDS_CONTACT`. Example:
```
User-Agent: wikitrends/0.1 (<repo-url>; ${WIKITRENDS_CONTACT})
```

## 1. Pageviews API (per-article)

**Endpoint**:  
`https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}`

**Example call** (Ukrainian Wikipedia, article "Астрономія", daily, 2024-01-01 to 2024-03-31):
```
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/uk.wikipedia/all-access/user/%D0%90%D1%81%D1%82%D1%80%D0%BE%D0%BD%D0%BE%D0%BC%D1%96%D1%8F/daily/20240101/20240331
```

**Response shape** (JSON):
```json
{
  "items": [
    {
      "project": "uk.wikipedia",
      "article": "Астрономія",
      "granularity": "daily",
      "timestamp": "2024010100",
      "access": "all-access",
      "agent": "user",
      "views": 46
    },
    ...
  ]
}
```
- `timestamp` format: `YYYYMMDDHH` (hourly granularity, but for daily data the hour is always `00`).
- `views`: integer number of views.
- The `article` field is URL-encoded in the request but returned as the original Unicode string (escaped in JSON).
- The array is ordered by timestamp ascending.
- **Note**: Days with zero views are omitted from the `items` array. If an article has no views for the entire requested range (e.g., future dates), the API returns HTTP 404 with a problem+json body (see section 6).

**Headers observed**:
- `content-type: application/json; charset=utf-8`
- `cache-control: s-maxage=14400, max-age=14400`
- `age`: seconds since last hit in cache (0 for miss).
- `x-cache`: indicates cache hit/miss.
- No explicit rate-limit headers (like `X-RateLimit`) were observed, but the API enforces rate limits; clients should respect 429 responses and implement backoff.

## 2. Pageviews API (aggregate)

**Endpoint**:  
`https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/{project}/{access}/{agent}/{granularity}/{start}/{end}`

**Example call** (Ukrainian Wikipedia, monthly, 2024-01 to 2024-06):
```
https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/uk.wikipedia/all-access/user/monthly/20240101/20240630
```

**Response shape**:
```json
{
  "items": [
    {
      "project": "uk.wikipedia",
      "access": "all-access",
      "agent": "user",
      "granularity": "monthly",
      "timestamp": "2024010100",
      "views": 115282138
    },
    ...
  ]
}
```
- Same structure as per-article but without `article` field.
- `timestamp` first day of the month at hour 00.
- `views`: total views for that month.

**Headers**: similar to per-article endpoint.

## 3. Wikidata API – wbsearchentities

**Endpoint**:  
`https://www.wikidata.org/w/api.php`

**Parameters**:
- `action=wbsearchentities`
- `search=<string>`
- `language=<language code>` (e.g., `en`)
- `format=json`

**Example call** (search for "astronomy" in English):
```
https://www.wikidata.org/w/api.php?action=wbsearchentities&search=astronomy&language=en&format=json
```

**Response shape**:
```json
{
  "searchinfo": {
    "search": "astronomy"
  },
  "search": [
    {
      "id": "Q333",
      "title": "Q333",
      "pageid": 526,
      "concepturi": "http://www.wikidata.org/entity/Q333",
      "repository": "wikidata",
      "url": "//www.wikidata.org/wiki/Q333",
      "display": {
        "label": {
          "value": "astronomy",
          "language": "en"
        },
        "description": {
          "value": "natural science studying celestial objects and phenomena in the cosmos",
          "language": "en"
        }
      },
      "label": "astronomy",
      "description": "natural science studying celestial objects and phenomena in the cosmos",
      "match": {
        "type": "label",
        "language": "en",
        "text": "astronomy"
      }
    },
    ...
  ],
  "search-continue": 7,
  "success": 1
}
```
- Each result includes basic entity info and a `display` object with label and description in the requested language.
- `match` indicates how the result matched the search term.
- The `search-continue` field, if present, indicates that more results are available (use `continue` parameter to paginate).

**Headers**:
- `content-type: application/json; charset=utf-8`
- `cache-control: private, must-revalidate, max-age=0`
- `x-cache`: indicates cache status.

## 4. Wikidata API – wbgetentities (sitelinks)

**Endpoint**:  
`https://www.wikidata.org/w/api.php`

**Parameters** (following a wbsearchentities result):
- `action=wbgetentities`
- `ids=<entity ID>` (e.g., `Q333`)
- `props=sitelinks`
- `format=json`

**Example call**:
```
https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q333&props=sitelinks&format=json
```

**Response shape**:
```json
{
  "entities": {
    "Q333": {
      "type": "item",
      "id": "Q333",
      "sitelinks": {
        "ukwiki": {
          "site": "ukwiki",
          "title": "Астрономія",
          "badges": []
        },
        "enwiki": {
          "site": "enwiki",
          "title": "Astronomy",
          "badges": ["Q17437798"]
        },
        "commonswiki": {
          "site": "commonswiki",
          "title": "Astronomy",
          "badges": []
        },
        "specieswiki": {
          "site": "specieswiki",
          "title": "Astronomy",
          "badges": []
        },
        /* many other language and sister projects */
      }
    }
  },
  "success": 1
}
```
- Each entry under `sitelinks` corresponds to a Wikimedia project (identified by site code, e.g., `ukwiki` for Ukrainian Wikipedia, `commonswiki` for Wikimedia Commons, `specieswiki` for Wikispecies).
- `title` is the article title on that project.
- `badges` (if present) indicates special status like "featured article".
- Note: some site codes require mapping to the actual subdomain, e.g., `be_x_oldwiki` corresponds to `be-tarask.wikipedia.org`.

## 5. Wikipedia API – Query with redirects

**Endpoint**:  
`https://en.wikipedia.org/w/api.php` (or any language-specific Wikipedia)

**Parameters**:
- `action=query`
- `titles=<article title>` (URL-encoded)
- `redirects=1`
- `format=json`

**Example call** (checking for redirects from "Astronomy" on English Wikipedia):
```
https://en.wikipedia.org/w/api.php?action=query&prop=redirects&titles=Astronomy&format=json
```

**Response shape** (for `prop=redirects`):
```json
{
  "batchcomplete": "",
  "query": {
    "pages": {
      "50650": {
        "pageid": 50650,
        "ns": 0,
        "title": "Astronomy",
        "redirects": [
          {
            "pageid": 52038,
            "ns": 0,
            "title": "Stellar astronomy"
          },
          {
            "pageid": 102185,
            "ns": 0,
            "title": "Astronomical"
          },
          ...
        ]
      }
    }
  }
}
```
- The `redirects` array (if present) lists titles that redirect to the given title.

**Example call** (resolving a redirect title):
```
https://en.wikipedia.org/w/api.php?action=query&titles=Stellar%20astronomy&redirects=1&format=json
```

**Response shape** (for `titles` with `redirects=1`):
```json
{
  "batchcomplete": "",
  "query": {
    "redirects": [
      {
        "from": "Stellar astronomy",
        "to": "Astronomy",
        "tofragment": "Stellar"
      }
    ],
    "pages": {
      "50650": {
        "pageid": 50650,
        "ns": 0,
        "title": "Astronomy"
      }
    }
  }
}
```
- The `redirects` array shows the mapping from the input title to the target title.
- The `pages` object contains the target page (normalized title).
- If the input title is not a redirect, the `redirects` array is absent and the `pages` object contains the input title (with a positive pageid).

**Headers**:
- `content-type: application/json; charset=utf-8`
- `cache-control: private, must-revalidate, max-age=0`

## 6. Nonexistent Article (Pageviews API)

When requesting pageviews for an article that does not exist (or no data for the period), the Pageviews API returns HTTP 404.

**Example call**:
```
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/uk.wikipedia/all-access/user/ThisArticleDoesNotExist12345/daily/20240101/20240331
```

**Response shape** (JSON):
```json
{
  "detail": "The date(s) you used are valid, but we either do not have data for those date(s), or the project you asked for is not loaded yet. Please check documentation for more information",
  "method": "get",
  "status": 404,
  "title": "Not Found",
  "type": "about:blank",
  "uri": "/metrics/pageviews/per-article/uk.wikipedia/all-access/user/ThisArticleDoesNotExist12345/daily/20240101/20240331"
}
```
- Content-Type: `application/problem+json`
- The `detail` field explains the condition; it may vary slightly.
- The `uri` field echoes the requested path.
- Note: This same 404 response is also returned when requesting an existing article for a date range with no data (e.g., future dates).

**Headers**:
- `content-type: application/problem+json`
- `cache-control: s-maxage=600` (shorter caching for errors)
- `x-cache`: miss

## 7. Article Titles Containing Slashes

Article titles containing slash characters (e.g., "AC/DC") must be fully percent-encoded in the Pageviews API URL. Using `safe=''` in Python's `urllib.parse.quote` ensures that the slash is encoded as `%2F`.

**Example call** (English Wikipedia, article "AC/DC", daily, one day):
```
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/AC%2FDC/daily/20260923/20260924
```
This request returns a successful response with data for the article.

**Response shape** (JSON):
```json
{
  "items": [
    {
      "project": "en.wikipedia",
      "article": "AC/DC",
      "granularity": "daily",
      "timestamp": "2026092300",
      "access": "all-access",
      "agent": "user",
      "views": 5617
    }
  ]
}
```

## Rate Limits and Errors

- The APIs enforce rate limits; clients should handle HTTP 429 (Too Many Requests) with exponential backoff.
- Observed error responses include:
  - 404 for missing article data (as above).
  - 400 for malformed parameters (not observed but documented).
  - 5xx for server errors (should trigger retry).
- No `Retry-After` header was observed in the small sample, but clients should still implement backoff on 429/5xx.

## Notes on Data

- Data starts from July 2015 for pageviews.
- Aggregated endpoints return data per granularity (daily/monthly).
- For daily data, the API returns data for each day with a timestamp at hour 00.
- The "agent=user" excludes spiders and automated agents.
- "access=all-access" combines desktop, mobile web, and mobile app.

## Implementation Tips

- Cache every response on disk (key = URL) to avoid redundant requests.
- Only the current/incomplete day is not cached forever; historical data is stable.
- Requests should be strictly sequenced with a small delay (e.g., 100ms) to avoid hitting rate limits.
- Verify endpoints with live calls before coding against them (as done here).
- Save real responses as test fixtures; never invent response shapes.