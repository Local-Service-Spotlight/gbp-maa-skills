# GBP Proxy Workflow (Pipedream) - Stage 1

Read-only proxy that lets the GBP agent call Google Business Profile APIs live, using the OAuth connection Pipedream already holds. No storage. Google credentials never leave Pipedream.

## Setup (about 10 minutes)

1. **New project** in Pipedream, for example `GBP Agent`. Leave the Maps Visibility System project untouched.
2. **Environment variable**: Settings > Environment Variables > add `GBP_PROXY_KEY`. Use a long random value (40+ characters). Save it somewhere safe; the MCP server needs the same value later.
3. **New workflow** named `GBP Proxy - Read Only`.
4. **Trigger**: HTTP / Webhook.
   - Event Data: **Full HTTP request** (the code reads headers; "HTTP body only" will fail the key check).
   - HTTP Response: **Return a custom response from your workflow**.
   - Authorization: None (the code enforces the key header itself).
5. **Add one step**: Node.js code step, name it `gbp_proxy`. Paste the code below. Connect the existing Google Business Profile account when prompted.
6. **Workflow settings**: Timeout 120 seconds, Memory 256 MB. Turn on error notifications.
7. **Deploy**, then copy the trigger URL.

## Request format

`POST` to the trigger URL with header `x-gbp-proxy-key: <your key>` and a JSON body.

| op | Required fields | Optional fields |
|---|---|---|
| `list_locations` | none | none |
| `daily_metrics` | `location_id`, `start_date`, `end_date` | `metrics` (array) |
| `search_keywords` | `location_id`, `start_month`, `end_month` (YYYY-MM) | none |
| `reviews` | `location_id` | `account_id`, `max_reviews` (default 200) |
| `profile` | `location_id` | none |
| `media_posts` | `location_id` | `account_id` |

- `location_id` format: `locations/1234567890`
- `account_id` format: `accounts/1234567890`. If omitted on `reviews` or `media_posts`, the proxy finds it, which costs a few extra calls. `list_locations` returns it, so the MCP can pass it along.
- Dates are `YYYY-MM-DD`. Performance data lags 3 to 5 days, so the agent should end its window 5 days before today.

## Smoke test (run after deploy)

```bash
URL="https://YOUR-TRIGGER.m.pipedream.net"
KEY="your-proxy-key"

# 1. Access check and roster
curl -s -X POST "$URL" -H "Content-Type: application/json" -H "x-gbp-proxy-key: $KEY" \
  -d '{"op":"list_locations"}'

# 2. Metrics for one location (compare against the GBP dashboard for the same dates)
curl -s -X POST "$URL" -H "Content-Type: application/json" -H "x-gbp-proxy-key: $KEY" \
  -d '{"op":"daily_metrics","location_id":"locations/REPLACE","start_date":"2026-08-01","end_date":"2026-08-31"}'

# 3. Wrong key must return 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL" -H "Content-Type: application/json" \
  -H "x-gbp-proxy-key: wrong" -d '{"op":"list_locations"}'
```

Pass criteria: step 1 lists every client location you expect, step 2 totals match the dashboard for August, step 3 prints `401`.

## Code: `gbp_proxy` step

```javascript
import { axios } from "@pipedream/platform";
import qs from "qs";
import crypto from "crypto";

const PERF = "https://businessprofileperformance.googleapis.com/v1";
const INFO = "https://mybusinessbusinessinformation.googleapis.com/v1";
const ACCT = "https://mybusinessaccountmanagement.googleapis.com/v1";
const V4 = "https://mybusiness.googleapis.com/v4";

const DEFAULT_METRICS = [
  "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
  "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
  "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
  "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
  "CALL_CLICKS",
  "WEBSITE_CLICKS",
  "BUSINESS_DIRECTION_REQUESTS",
  "BUSINESS_CONVERSATIONS",
  "BUSINESS_BOOKINGS",
];

const PROFILE_MASK = [
  "name", "title", "storeCode", "languageCode", "phoneNumbers", "categories",
  "storefrontAddress", "websiteUri", "regularHours", "specialHours", "moreHours",
  "serviceArea", "serviceItems", "labels", "latlng", "openInfo", "metadata", "profile",
].join(",");

const STAR = { ONE: 1, TWO: 2, THREE: 3, FOUR: 4, FIVE: 5 };

class ProxyError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function parseYMD(s, field) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
  if (!m) throw new ProxyError(400, `${field} must be YYYY-MM-DD`);
  return { year: +m[1], month: +m[2], day: +m[3] };
}

function parseYM(s, field) {
  const m = /^(\d{4})-(\d{2})$/.exec(s || "");
  if (!m) throw new ProxyError(400, `${field} must be YYYY-MM`);
  return { year: +m[1], month: +m[2] };
}

function fmtDate(d) {
  if (!d || !d.year) return null;
  return `${d.year}-${String(d.month).padStart(2, "0")}-${String(d.day).padStart(2, "0")}`;
}

function checkLocation(id) {
  if (!/^locations\/\d+$/.test(id || "")) {
    throw new ProxyError(400, "location_id must look like locations/1234567890");
  }
  return id;
}

function checkAccount(id) {
  if (!/^accounts\/\d+$/.test(id || "")) {
    throw new ProxyError(400, "account_id must look like accounts/1234567890");
  }
  return id;
}

export default defineComponent({
  props: {
    google_my_business: { type: "app", app: "google_my_business" },
  },

  async run({ steps, $ }) {
    const respond = (status, body) =>
      $.respond({ status, headers: { "Content-Type": "application/json" }, body });

    const token = this.google_my_business.$auth.oauth_access_token;
    const get = (url, params = {}) =>
      axios($, {
        method: "GET",
        url,
        params,
        headers: { Authorization: `Bearer ${token}` },
        paramsSerializer: (p) => qs.stringify(p, { arrayFormat: "repeat" }),
      });

    // ---- paged helpers -------------------------------------------------
    const listAccounts = async () => {
      const out = [];
      let pageToken;
      do {
        const res = await get(`${ACCT}/accounts`, { pageSize: 20, pageToken });
        out.push(...(res.accounts || []));
        pageToken = res.nextPageToken;
      } while (pageToken);
      return out;
    };

    const listLocationsFor = async (account, readMask) => {
      const out = [];
      let pageToken;
      do {
        const res = await get(`${INFO}/${account}/locations`, { readMask, pageSize: 100, pageToken });
        out.push(...(res.locations || []));
        pageToken = res.nextPageToken;
      } while (pageToken);
      return out;
    };

    const resolveAccount = async (locationId, given) => {
      if (given) return checkAccount(given);
      for (const a of await listAccounts()) {
        const locs = await listLocationsFor(a.name, "name");
        if (locs.some((l) => l.name === locationId)) return a.name;
      }
      throw new ProxyError(404, `${locationId} not found under any accessible account`);
    };

    // ---- ops -----------------------------------------------------------
    const ops = {
      async list_locations() {
        const result = [];
        for (const a of await listAccounts()) {
          const locs = await listLocationsFor(
            a.name, "name,title,storefrontAddress,websiteUri,categories,metadata"
          );
          for (const l of locs) {
            result.push({
              account_id: a.name,
              account_name: a.accountName,
              location_id: l.name,
              title: l.title,
              primary_category: l.categories?.primaryCategory?.displayName || null,
              city: l.storefrontAddress?.locality || null,
              state: l.storefrontAddress?.administrativeArea || null,
              website: l.websiteUri || null,
              maps_uri: l.metadata?.mapsUri || null,
              place_id: l.metadata?.placeId || null,
            });
          }
        }
        return { count: result.length, locations: result };
      },

      async daily_metrics(b) {
        const loc = checkLocation(b.location_id);
        const s = parseYMD(b.start_date, "start_date");
        const e = parseYMD(b.end_date, "end_date");
        if (fmtDate(s) > fmtDate(e)) throw new ProxyError(400, "start_date is after end_date");
        const metrics = Array.isArray(b.metrics) && b.metrics.length ? b.metrics : DEFAULT_METRICS;
        if (!metrics.every((m) => /^[A-Z_]+$/.test(m))) throw new ProxyError(400, "invalid metric name");

        const res = await get(`${PERF}/${loc}:fetchMultiDailyMetricsTimeSeries`, {
          dailyMetrics: metrics,
          "dailyRange.startDate.year": s.year,
          "dailyRange.startDate.month": s.month,
          "dailyRange.startDate.day": s.day,
          "dailyRange.endDate.year": e.year,
          "dailyRange.endDate.month": e.month,
          "dailyRange.endDate.day": e.day,
        });

        const series = (res.multiDailyMetricTimeSeries || []).flatMap((x) => x.dailyMetricTimeSeries || []);
        const rows = [];
        const totals = {};
        for (const sr of series) {
          totals[sr.dailyMetric] = 0;
          for (const v of sr.timeSeries?.datedValues || []) {
            const date = fmtDate(v.date);
            if (!date) continue;
            const value = v.value ? parseInt(v.value, 10) : 0;
            rows.push({ date, metric: sr.dailyMetric, value });
            totals[sr.dailyMetric] += value;
          }
        }
        return { start_date: fmtDate(s), end_date: fmtDate(e), totals, rows };
      },

      async search_keywords(b) {
        const loc = checkLocation(b.location_id);
        const s = parseYM(b.start_month, "start_month");
        const e = parseYM(b.end_month, "end_month");
        const keywords = [];
        let pageToken;
        do {
          const res = await get(`${PERF}/${loc}/searchkeywords/impressions/monthly`, {
            "monthlyRange.startMonth.year": s.year,
            "monthlyRange.startMonth.month": s.month,
            "monthlyRange.endMonth.year": e.year,
            "monthlyRange.endMonth.month": e.month,
            pageSize: 100,
            pageToken,
          });
          for (const k of res.searchKeywordsCounts || []) {
            const iv = k.insightsValue || {};
            keywords.push({
              keyword: k.searchKeyword,
              impressions: iv.value ? parseInt(iv.value, 10) : null,
              // Google hides exact counts for low-volume terms and returns a threshold instead
              below_threshold: iv.threshold ? parseInt(iv.threshold, 10) : null,
            });
          }
          pageToken = res.nextPageToken;
        } while (pageToken && keywords.length < 1000);
        keywords.sort((a, c) => (c.impressions || 0) - (a.impressions || 0));
        return { start_month: b.start_month, end_month: b.end_month, count: keywords.length, keywords };
      },

      async reviews(b) {
        const loc = checkLocation(b.location_id);
        const account = await resolveAccount(loc, b.account_id);
        const cap = Math.min(parseInt(b.max_reviews, 10) || 200, 1000);
        const reviews = [];
        let pageToken, averageRating = null, totalReviewCount = null;
        do {
          const res = await get(`${V4}/${account}/${loc}/reviews`, {
            pageSize: 50, orderBy: "updateTime desc", pageToken,
          });
          averageRating = res.averageRating ?? averageRating;
          totalReviewCount = res.totalReviewCount ?? totalReviewCount;
          for (const r of res.reviews || []) {
            reviews.push({
              review_id: r.reviewId,
              rating: STAR[r.starRating] || null,
              comment: r.comment || null,
              reviewer: r.reviewer?.displayName || null,
              created_at: r.createTime,
              updated_at: r.updateTime,
              has_reply: Boolean(r.reviewReply),
              reply_at: r.reviewReply?.updateTime || null,
            });
          }
          pageToken = res.nextPageToken;
        } while (pageToken && reviews.length < cap);
        return {
          account_id: account,
          average_rating: averageRating,
          total_review_count: totalReviewCount,
          returned: reviews.length,
          truncated: Boolean(pageToken),
          reviews,
        };
      },

      async profile(b) {
        const loc = checkLocation(b.location_id);
        const location = await get(`${INFO}/${loc}`, { readMask: PROFILE_MASK });
        let attributes = null, attributes_error = null;
        try {
          const res = await get(`${INFO}/${loc}/attributes`);
          attributes = res.attributes || [];
        } catch (err) {
          attributes_error = err.message;
        }
        return { location, attributes, attributes_error };
      },

      async media_posts(b) {
        const loc = checkLocation(b.location_id);
        const account = await resolveAccount(loc, b.account_id);
        const out = { account_id: account };
        try {
          const m = await get(`${V4}/${account}/${loc}/media`, { pageSize: 100 });
          const items = m.mediaItems || [];
          out.media = {
            total_count: m.totalMediaItemCount ?? items.length,
            latest_created_at: items.map((i) => i.createTime).filter(Boolean).sort().pop() || null,
            by_format: items.reduce((acc, i) => { acc[i.mediaFormat] = (acc[i.mediaFormat] || 0) + 1; return acc; }, {}),
          };
        } catch (err) { out.media_error = err.message; }
        try {
          const p = await get(`${V4}/${account}/${loc}/localPosts`, { pageSize: 20 });
          const posts = p.localPosts || [];
          out.posts = {
            returned: posts.length,
            latest_created_at: posts.map((x) => x.createTime).filter(Boolean).sort().pop() || null,
            recent: posts.slice(0, 10).map((x) => ({
              created_at: x.createTime, topic_type: x.topicType, state: x.state,
              summary: (x.summary || "").slice(0, 200),
            })),
          };
        } catch (err) { out.posts_error = err.message; }
        return out;
      },
    };

    // ---- request handling ---------------------------------------------
    try {
      const event = steps.trigger.event;
      const headers = event.headers || {};
      const expected = process.env.GBP_PROXY_KEY || "";
      const supplied = String(headers["x-gbp-proxy-key"] || "");
      const a = Buffer.from(supplied), e = Buffer.from(expected);
      if (!expected || a.length !== e.length || !crypto.timingSafeEqual(a, e)) {
        throw new ProxyError(401, "unauthorized");
      }
      if (event.method !== "POST") throw new ProxyError(405, "POST only");

      const body = event.body && typeof event.body === "object" ? event.body : {};
      const op = body.op;
      if (!Object.prototype.hasOwnProperty.call(ops, op)) {
        throw new ProxyError(400, `unknown op. allowed: ${Object.keys(ops).join(", ")}`);
      }

      const data = await ops[op](body);
      await respond(200, {
        ok: true, op, location_id: body.location_id || null,
        fetched_at: new Date().toISOString(), data,
      });
      return { op, location_id: body.location_id || null, ok: true };
    } catch (err) {
      const status = err instanceof ProxyError ? err.status : (err.response?.status || 502);
      const detail = err.response?.data?.error?.message || err.message;
      await respond(status, { ok: false, error: detail, status });
      return { ok: false, status, error: detail };
    }
  },
});
```

## Design notes

- **Read-only by construction.** Every call is a GET, the op list is a fixed allowlist, and IDs are format-checked, so the proxy cannot post, reply, or edit anything even if the key leaks.
- **No SQL, no storage.** The injection and first-of-month date issues from the old worker do not exist here: dates are parsed as strings into year/month/day parts with no `Date` arithmetic.
- **Low-volume keywords.** Google withholds exact counts for rare terms and returns a threshold instead. The proxy keeps both fields so the agent can report "fewer than N" accurately.
- **Reviews cap.** Default 200 most recent, max 1000. `average_rating` and `total_review_count` always reflect the full profile, and `truncated` tells the agent when the list is partial.
- **Untested against your account.** I wrote this from the API specs and your working `backfill_pull` call. The smoke test is the verification step; send me any error body and I will fix it.
