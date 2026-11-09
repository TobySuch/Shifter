# Serving downloads from your reverse proxy

By default Shifter streams every download through Django. If you run Shifter
behind nginx, Caddy or Traefik, you can let the proxy send the file instead:

- The proxy serves files much more efficiently than Python does.
- Downloads support HTTP Range requests, so interrupted downloads can be
  resumed and download managers can fetch a file over several connections.
- Long or slow downloads don't occupy one of Shifter's worker threads.

Shifter still decides whether a download is allowed (the file exists and
hasn't expired). It replies with an empty response that carries an
`X-Accel-Redirect` header naming the stored file, and the proxy sends that
file from disk.

## 1. Enable it in Shifter

Set the internal URL prefix in your `.env` file:

```
X_ACCEL_REDIRECT_PREFIX=/protected-media/
```

> [!WARNING]
> Only set this when your proxy is configured as below. Without a proxy
> handling the header, every download is an empty file. Don't let users reach
> Shifter's port 8000 directly.

## 2. Give the proxy access to the media volume

The proxy needs to read Shifter's `media` volume. Mount it **read-only**, and
never serve it at a public URL: files must only be reachable through Shifter,
which checks expiry. In the examples below the volume is mounted at `/media`
in the proxy container.

```yaml
volumes:
  db:
  media:

services:
  shifter:
    image: ghcr.io/tobysuch/shifter:latest
    restart: always
    volumes:
      - media:/home/app/web/media
      - db:/home/app/web/db
    env_file:
      - .env
    # No "ports:" here; only the proxy is published.
```

## nginx

```yaml
  nginx:
    image: nginx:alpine
    restart: always
    depends_on:
      - shifter
    ports:
      - 80:80
    volumes:
      - media:/media:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

`nginx.conf`:

```nginx
server {
    listen 80;
    # Must be larger than UPLOAD_CHUNK_SIZE (8MB by default).
    client_max_body_size 20m;

    location / {
        proxy_pass http://shifter:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Only reachable through X-Accel-Redirect responses from Shifter.
    location /protected-media/ {
        internal;
        alias /media/;
    }
}
```

`internal` makes nginx return 404 if someone requests `/protected-media/...`
directly.

## Caddy

```yaml
  caddy:
    image: caddy:alpine
    restart: always
    ports:
      - 80:80
      - 443:443
    volumes:
      - media:/media:ro
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
```

`Caddyfile`:

```
shifter.mydomain.com {
	reverse_proxy shifter:8000 {
		@accel header X-Accel-Redirect *
		handle_response @accel {
			root * /media
			rewrite * {rp.header.X-Accel-Redirect}
			uri strip_prefix /protected-media
			method * GET
			header Content-Disposition {rp.header.Content-Disposition}
			header Content-Type {rp.header.Content-Type}
			file_server
		}
	}
}
```

The two `header` lines keep the download's filename and type from Shifter's
response. Requests for `/protected-media/...` from browsers go to Shifter like
any other URL, which returns 404.

## Traefik

Traefik can't serve files itself, so it can't act on `X-Accel-Redirect`. Put a
small nginx container between Traefik and Shifter, configured as in the
[nginx](#nginx) section above (it doesn't need `ports:`), and point Traefik at
nginx instead of Shifter:

```yaml
  nginx:
    image: nginx:alpine
    restart: always
    depends_on:
      - shifter
    volumes:
      - media:/media:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    labels:
      - traefik.enable=true
      - traefik.http.routers.shifter.rule=Host(`shifter.mydomain.com`)
      - traefik.http.routers.shifter.entrypoints=websecure
      - traefik.http.routers.shifter.tls.certresolver=myresolver
      - traefik.http.services.shifter.loadbalancer.server.port=80
```

Remove any Traefik labels from the `shifter` service, so all traffic goes
through nginx. Adjust the entrypoint and certificate resolver names to match
your Traefik setup.

## Checking it works

Download a file and look at the response headers:

```bash
curl -sI https://shifter.mydomain.com/f/<file id>
```

You should see your proxy's `Server` header (or no Shifter one),
`Accept-Ranges: bytes` and the file's real `Content-Length`. An
`X-Accel-Redirect` header or `Content-Length: 0` means the proxy didn't handle
the response.
