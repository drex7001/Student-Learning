FROM node:22-alpine

WORKDIR /app

COPY web/package*.json ./web/
RUN cd web && npm install

COPY web ./web

WORKDIR /app/web

RUN npm run build

CMD ["npm", "run", "start"]
