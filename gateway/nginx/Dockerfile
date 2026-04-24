# ./gateway/nginx/Dockerfile
FROM nginx:1.25-alpine

# Удаляем дефолтный конфиг
RUN rm /etc/nginx/conf.d/default.conf

# Копируем наш конфиг
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Пробрасываем порт
EXPOSE 80

# Nginx запускается автоматически при старте образа
CMD ["nginx", "-g", "daemon off;"]