# Frontend image for the "full" Compose profile. Build context is the repository root
# (the app uses brand media from assets/). Dev normally runs `npm run dev` on the host.
FROM node:22-alpine AS build
WORKDIR /src/app/frontend
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY assets/logos /src/assets/logos
COPY app/frontend ./
RUN npm run build

FROM nginx:1.29-alpine
COPY app/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/app/frontend/dist /usr/share/nginx/html
EXPOSE 80
