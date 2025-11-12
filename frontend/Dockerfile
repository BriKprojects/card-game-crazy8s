# Stage 1: build the frontend assets
FROM node:20-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
ARG VITE_BACKEND_URL=http://card-gops-backend:8000
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
RUN npm run build

# Stage 2: serve the built assets via Vite preview
FROM node:20-slim AS runner
ARG VITE_BACKEND_URL=http://card-gops-backend:8000
WORKDIR /app
COPY --from=build /app/package*.json ./
RUN npm install --omit=dev

COPY --from=build /app/dist ./dist
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
EXPOSE 5173
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]