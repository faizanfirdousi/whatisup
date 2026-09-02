export const config = {
  api: { bodyParser: false },
};

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function backendOrigin() {
  const raw = process.env.BACKEND_URL || "";
  return raw.replace(/\/+$/, "");
}

function targetPath(req) {
  const p = req.query?.p;
  if (Array.isArray(p)) return p[0] || "/";
  if (typeof p === "string" && p.startsWith("/")) return p;
  const url = new URL(req.url, "http://localhost");
  return url.pathname;
}

function forwardedSearch(req) {
  const url = new URL(req.url, "http://localhost");
  url.searchParams.delete("p");
  const qs = url.searchParams.toString();
  return qs ? `?${qs}` : "";
}

async function readBody(req) {
  if (req.method === "GET" || req.method === "HEAD") return undefined;
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return undefined;
  return Buffer.concat(chunks);
}

export default async function handler(req, res) {
  const origin = backendOrigin();
  if (!origin) {
    res.status(500).json({ detail: "BACKEND_URL is not configured on Vercel" });
    return;
  }

  const target = `${origin}${targetPath(req)}${forwardedSearch(req)}`;
  const headers = {};
  for (const [key, value] of Object.entries(req.headers)) {
    if (!value || HOP_BY_HOP.has(key.toLowerCase())) continue;
    headers[key] = Array.isArray(value) ? value.join(",") : value;
  }
  headers["x-forwarded-host"] = req.headers.host || "whatisupp.vercel.app";
  headers["x-forwarded-proto"] = "https";

  let upstream;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: await readBody(req),
      redirect: "manual",
    });
  } catch {
    res.status(502).json({ detail: "Upstream API is unreachable" });
    return;
  }

  res.status(upstream.status);
  upstream.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key) || key === "content-encoding") return;
    if (key === "set-cookie") return;
    res.setHeader(key, value);
  });
  const cookies = typeof upstream.headers.getSetCookie === "function" ? upstream.headers.getSetCookie() : [];
  for (const cookie of cookies) {
    res.appendHeader("Set-Cookie", cookie);
  }

  const buf = Buffer.from(await upstream.arrayBuffer());
  res.send(buf);
}
