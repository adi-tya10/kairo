FROM node:18-alpine AS base

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install

COPY apps/web/ ./
RUN npm run build

EXPOSE 3000
ENV PORT=3000

CMD ["npm", "run", "start"]
