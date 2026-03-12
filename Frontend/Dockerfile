# ---- Builder Stage ----
# 使用 Node.js 18 LTS 版本作为构建环境 (您可以根据需要调整)
FROM node:18 AS builder

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 lock 文件
# 优化缓存：仅当包文件变化时才重新安装依赖
COPY package.json package-lock.json* ./

# 安装所有依赖
RUN npm install

# 复制项目所有源代码
COPY . .

# 设置构建时环境变量（这些将嵌入到构建的代码中）
# 如果要在构建时使用系统环境变量覆盖，可以在docker build命令中使用--build-arg参数
ARG MEDSYNTHAI_FRONTEND_API_HOST=127.0.0.1
ARG MEDSYNTHAI_FRONTEND_API_PORT=8001
ENV MEDSYNTHAI_FRONTEND_API_HOST=${MEDSYNTHAI_FRONTEND_API_HOST}
ENV MEDSYNTHAI_FRONTEND_API_PORT=${MEDSYNTHAI_FRONTEND_API_PORT}

# 执行 Next.js 生产构建 (确保 next.config.ts 中配置了 output: 'standalone')
RUN npm run build

# --- 添加调试步骤 (可选，确认构建产物) ---
# 打印出 /app 目录下的内容，检查 .next/standalone 和 .next/static 是否生成
RUN echo "--- Debug: Listing /app contents after build ---" && ls -la /app && echo "--- Debug: Listing /app/.next contents after build ---" && ls -la /app/.next
# --- 结束调试步骤 ---

# ---- Runner Stage ----
# 使用轻量的 Node.js Alpine 镜像运行生产服务
FROM node:18-alpine AS runner

WORKDIR /app

# 设置 Node.js 生产环境
ENV NODE_ENV=production

# 设置运行时环境变量
# 这些变量可以在容器启动时通过 -e 参数覆盖
# 例如: docker run -e MEDSYNTHAI_FRONTEND_API_HOST=api.example.com -e MEDSYNTHAI_FRONTEND_API_PORT=8080 -p 3000:3000 your-image-name
ENV MEDSYNTHAI_FRONTEND_API_HOST=127.0.0.1
ENV MEDSYNTHAI_FRONTEND_API_PORT=8001

# 从 builder 阶段复制 standalone 输出和静态资源
# standalone 输出包含了运行所需的最小化 node_modules 和 server.js
COPY --from=builder /app/.next/standalone ./
# .next/static 包含了构建后的静态资源 (JS, CSS, etc.)
COPY --from=builder /app/.next/static ./.next/static

# 暴露 Next.js 生产服务器监听的端口 (默认为 3000)
EXPOSE 3000

# 启动 Next.js 生产服务器 (standalone 模式下使用 server.js)
# CMD 命令需要相对于 WORKDIR (/app)，因为 standalone 输出复制到了 ./
CMD ["node", "server.js"]

#test 1