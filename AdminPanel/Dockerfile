FROM node:latest

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with npm
RUN npm install

# Copy application code
COPY . .

# Create .env.local file with MongoDB URI
RUN echo "MONGODB_URL=mongodb://admin:admin@mongo-service:27017" > .env.local

# Build the Next.js app
RUN npm run build

# Expose port for Next.js
EXPOSE 3000

# Start the Next.js application
CMD ["npm", "run", "start"]

