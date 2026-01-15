FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000

RUN npm run build
CMD ["npm", "run", "start", "--", "-p", "3000"]
