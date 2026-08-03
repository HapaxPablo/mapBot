# webapp/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_URL
ARG VITE_MAP_STYLE_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html