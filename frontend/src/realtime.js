// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
// "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.

let clientPromise

function socketOrigin() {
  const { protocol, hostname, port } = window.location
  const socketPort = window.lumenpos_socketio_port
  const useSocketPort = window.lumenpos_socketio_dev && socketPort
  return `${protocol}//${hostname}${useSocketPort ? `:${socketPort}` : port ? `:${port}` : ''}`
}

function loadSocketClient() {
  if (window.io) return Promise.resolve(window.io)
  if (clientPromise) return clientPromise

  clientPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `${socketOrigin()}/socket.io/socket.io.js`
    script.async = true
    script.onload = () => {
      if (window.io) resolve(window.io)
      else reject(new Error('Socket.IO client script loaded without exposing io'))
    }
    script.onerror = () => reject(new Error('Could not load the Socket.IO client'))
    document.head.appendChild(script)
  }).catch((error) => {
    clientPromise = null
    throw error
  })

  return clientPromise
}

export async function connectRealtime() {
  const io = await loadSocketClient()
  const site = window.lumenpos_socketio_site
  const namespace = site ? `/${encodeURIComponent(site)}` : ''
  const socket = io(`${socketOrigin()}${namespace}`, {
    withCredentials: true,
    reconnection: true,
    reconnectionAttempts: Infinity,
  })
  return socket
}
