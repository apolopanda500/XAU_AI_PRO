FROM node:22-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

RUN npm run build

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]