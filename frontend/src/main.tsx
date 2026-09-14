import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './theme/global.css';
import './theme/quantum.css';
import './theme/wallpapers.css';
import './theme/mining.css';
import './theme/clock.css';
import './theme/mini-info.css';


// Ajusta para Tauri (mobile viewport)
const metaViewport = document.querySelector('meta[name="viewport"]');
if (metaViewport) {
  metaViewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);







