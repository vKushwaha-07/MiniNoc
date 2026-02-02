# Build Stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files (Use package.json AND package-lock.json if available)
COPY package*.json ./

# Install dependencies
RUN npm ci --silent || npm install

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production Stage
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from build stage to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
