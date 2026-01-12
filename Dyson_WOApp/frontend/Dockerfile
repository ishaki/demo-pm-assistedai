# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Build argument for API URL
ARG REACT_APP_API_URL=http://localhost:8000/api/v1

# Set environment variable from build arg
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the application with environment variable
RUN npm run build

# Production stage
FROM nginx:alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy built files from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
