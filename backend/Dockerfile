FROM node:22-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

# SEM `npm run build`
# --------------------
# Este `RUN` quebrava o build da imagem. O script `build` era `nitro build`, e o
# Nitro foi REMOVIDO do projeto em 04/10/2026 (commit 0e242f9): o backend passou
# a ser express puro em `server-desktop.cjs`, servido por `npm start`.
#
# O sintoma era `npm error Missing script: "build"` — a imagem nunca era
# construida, e o job `Docker` do CI reprovava.
#
# O `CMD` tambem apontava para `.output/server/index.mjs`, que e a saida do
# Nitro e nao existe mais.
EXPOSE 3000

CMD ["npm", "start"]