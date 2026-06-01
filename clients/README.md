# WeAgent Clients

This directory contains independent multi-platform clients. The existing
`frontend/` web app is intentionally left unchanged.

## Desktop

Electron client:

```bash
cd clients/desktop
npm install
npm run dev
```

The desktop client connects to an external backend configured by the user.

## Android

Capacitor Android client:

```bash
cd clients/android
npm install
npm run build
npx cap add android
npx cap sync android
npx cap open android
```

For LAN testing, configure the app with the backend machine address, for
example `http://192.168.1.100:5002`. Android phones cannot use
`http://localhost:5002` to reach a backend running on a computer.
