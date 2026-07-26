FROM node:22-alpine

WORKDIR /app

COPY web/package*.json ./web/
RUN cd web && npm ci

COPY web ./web

WORKDIR /app/web

# Next serialises `rewrites()` into the routes manifest at build time, so the API
# origin has to be known here rather than only at run time. It defaults to the
# compose service name; override with --build-arg for a different topology.
ARG API_ORIGIN=http://api:8000
ENV API_ORIGIN=${API_ORIGIN}

RUN npm run build

CMD ["npm", "run", "start"]
