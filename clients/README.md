# WeAgent Clients

`clients/` 存放 Web 主站之外的独立客户端。它们都连接外部 WeAgent 后端，不在客户端内嵌后端服务。

## 客户端范围

| 目录 | 类型 | 技术 | 当前定位 |
|---|---|---|---|
| `desktop/` | 桌面端 | Electron + Vite + Vue 2 | 功能全量迁移，面向日常使用和打包分发 |
| `android/` | Android 端 | Capacitor + Vite + Vue 2 | 主要功能迁移，优先登录、会话、Agent、设置 |

## 后端地址配置

客户端启动后需要配置后端服务地址。

- 本机桌面端连接本机后端：`http://127.0.0.1:5002`
- 局域网设备连接电脑后端：`http://<电脑局域网IP>:5002`
- Android 真机不能使用 `localhost` 访问电脑后端。

确认后端可访问：

```powershell
curl http://127.0.0.1:5002/api/health
```

## Desktop

```powershell
cd clients/desktop
npm install
npm run dev
```

构建前端资源：

```powershell
npm run build
```

打包安装程序：

```powershell
npm run electron:build
```

输出目录：

```text
clients/desktop/release/
```

说明：

- 应用名：`WeAgent`
- 图标源文件：`clients/desktop/logo.png`
- Windows 图标：构建时生成 `logo.ico`
- 打包时使用 `electron-builder`
- 国内网络下脚本已配置 electron-builder 二进制镜像源

常见问题：

- 点击某些页面侧栏入口数量不一致：优先检查 `src/components/Sidebar/index.vue` 和各页面内手写 sidebar 是否一致。
- 后端连接失败：检查客户端中配置的后端地址、电脑防火墙、后端监听地址和端口。
- 打包下载依赖失败：检查 npm 镜像、代理和 electron-builder 二进制镜像源。

## Android

```powershell
cd clients/android
npm install
npm run build
npm run cap:sync
npm run cap:open
```

首次生成 Android 工程：

```powershell
npm run cap:add:android
```

Android Studio 中运行前请确认：

- 已安装 Android SDK Platform，当前工程常用 `android-34`。
- 已配置 Gradle 代理或镜像，能下载 Gradle distribution。
- 已创建模拟器，或真机已打开 USB 调试。
- 后端地址填写电脑局域网 IP。

常见问题：

- `No target device found`：没有可用模拟器或真机。
- `Could not find compile target android-34`：SDK Platforms 中未安装 Android 34。
- `Connection timed out` 或 Gradle 下载失败：配置 Android Studio/Gradle 代理或镜像。
- 图片加载被拦截：调试阶段允许 HTTP，生产环境建议切 HTTPS。

## 功能对齐原则

- Web 是主功能基准。
- Desktop 尽量保持 Web 功能完整，包括会话、Agent、设置、收藏、工具集、产物工作台和工作流预览。
- Android 按移动端交互重写，不强求布局完全一致。
- 后端接口应保持跨端一致，端侧只处理视图和交互差异。

## 变更建议

- 客户端新增公共入口时，优先抽公共 Sidebar，避免各页面重复写入口。
- 跨端同步功能时，先确认 Web 行为，再迁移 Desktop，最后迁移 Android。
- 完成阶段性客户端变更后，至少运行对应端 `npm run build`。
