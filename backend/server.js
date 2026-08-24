/**
 * Crypto Trader Pro - API Backend
 * Versão: 1.10.0
 * Descrição: API REST para integração com frontend Electron e MT5
 */

const express = require('express');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend/dist')));

// Rota principal
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/dist/index.html'));
});

// API de status
app.get('/api/status', (req, res) => {
  res.json({
    status: "online",
    version: "1.10.0",
    timestamp: new Date().toISOString(),
    integrations: {
      mt5: false,
      ai_local: false,
      ai_cloud: false,
      github: true
    }
  });
});

// WebSocket para dados em tempo real
io.on('connection', (socket) => {
  console.log('Cliente conectado:', socket.id);
  
  // Simulação de dados de mercado
  setInterval(() => {
    const mockData = {
      symbol: "XAUUSD",
      price: (Math.random() * 100 + 1900).toFixed(2),
      timestamp: new Date().toISOString()
    };
    socket.emit('market_data', mockData);
  }, 5000);
  
  socket.on('disconnect', () => {
    console.log('Cliente desconectado:', socket.id);
  });
});

// Inicia servidor
server.listen(PORT, () => {
  console.log(`API Backend rodando na porta ${PORT}`);
  console.log(`Versão: 1.10.0`);
});