FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["sh", "-lc", "npm run build && mkdir -p .next/standalone/.next/static && cp -R .next/static/. .next/standalone/.next/static && if [ -d public ]; then mkdir -p .next/standalone/public && cp -R public/. .next/standalone/public; fi && node .next/standalone/server.js"]
