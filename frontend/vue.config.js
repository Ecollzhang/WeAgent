const { defineConfig } = require('@vue/cli-service')

const backendHost = process.env.BACKEND_HOST || '127.0.0.1'
const backendPort = process.env.BACKEND_PORT || '5002'
const backendTarget = process.env.BACKEND_PROXY_TARGET || `http://${backendHost}:${backendPort}`

module.exports = defineConfig({
  transpileDependencies: [],
  // parallel: false, 根据需要自己开启或关闭
  devServer: {
    port: 8080,
    historyApiFallback: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/uploads': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/socket.io': {
        target: backendTarget,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
