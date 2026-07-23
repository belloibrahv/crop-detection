# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Accept the API base URL at build time (Vite bakes it into the JS bundle)
ARG VITE_API_BASE_URL=http://localhost:5000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
