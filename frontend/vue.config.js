const { defineConfig } = require('@vue/cli-service')

const backendHost = process.env.BACKEND_HOST || '127.0.0.1'
const backendPort = process.env.BACKEND_PORT || '5002'
const backendTarget = process.env.BACKEND_PROXY_TARGET || `http://${backendHost}:${backendPort}`

module.exports = defineConfig({
  transpileDependencies: [],
  chainWebpack: (config) => {
    config.plugin('html').tap((args) => {
      const [options = {}] = args
      options.filename = 'index.html'
      options.template = './public/index.html'
      return [options]
    })

    config.plugin('copy').tap((args) => {
      const [options = {}] = args
      const patterns = Array.isArray(options.patterns) ? options.patterns : []
      options.patterns = patterns.map((pattern) => {
        const globOptions = pattern.globOptions || {}
        const ignore = Array.isArray(globOptions.ignore) ? globOptions.ignore.slice() : []
        for (const entry of ['index.html', '**/index.html']) {
          if (!ignore.includes(entry)) {
            ignore.push(entry)
          }
        }
        return {
          ...pattern,
          globOptions: {
            ...globOptions,
            ignore,
          },
        }
      })
      return [options]
    })
  },
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
