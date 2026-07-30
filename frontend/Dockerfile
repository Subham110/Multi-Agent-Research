FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_API_URL=http://localhost:8000/api/v1
ARG VITE_WS_URL=ws://localhost:8000/api/v1/ws
ENV VITE_API_URL=$VITE_API_URL VITE_WS_URL=$VITE_WS_URL
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://localhost/healthz || exit 1
