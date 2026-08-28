FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Relative API base — nginx in EACH stack proxies /api/ to ITS OWN backend.
# The old absolute default (http://IP/api/v1 = the ORIGINAL stack's port 80)
# made every copy's frontend silently talk to the original backend: edits on
# copy 2 "reflected" on copy 1. Relative keeps one build correct for every
# copy, port, and any future domain.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
