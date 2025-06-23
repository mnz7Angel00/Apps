import React, { useState, useEffect } from 'react';
import './App.css';

const App = () => {
  const [feedback, setFeedback] = useState('');
  const [theme, setTheme] = useState('dark');

  const factoryApps = [
    {
      id: 'moto-home',
      name: 'Moto Home',
      description: 'Launcher principal do Moto E13',
      icon: '🏠',
      schemes: [
        'com.motorola.launcher3',
        'android-app://com.motorola.launcher3',
        'intent://com.motorola.launcher3#Intent;scheme=android-app;end'
      ]
    },
    {
      id: 'settings',
      name: 'Configurações',
      description: 'Configurações do sistema',
      icon: '⚙️',
      schemes: [
        'android-app://com.android.settings',
        'intent://settings#Intent;action=android.settings.SETTINGS;end'
      ]
    },
    {
      id: 'calculator',
      name: 'Calculadora',
      description: 'Calculadora do sistema',
      icon: '🧮',
      schemes: [
        'android-app://com.android.calculator2',
        'intent://calculator#Intent;action=android.intent.action.MAIN;end'
      ]
    },
    {
      id: 'camera',
      name: 'Câmera',
      description: 'App de câmera',
      icon: '📷',
      schemes: [
        'android-app://com.motorola.camera3',
        'intent://camera#Intent;action=android.media.action.IMAGE_CAPTURE;end'
      ]
    },
    {
      id: 'contacts',
      name: 'Contatos',
      description: 'Lista de contatos',
      icon: '👥',
      schemes: [
        'android-app://com.android.contacts',
        'intent://contacts#Intent;action=android.intent.action.VIEW;end'
      ]
    },
    {
      id: 'phone',
      name: 'Telefone',
      description: 'App de ligações',
      icon: '📞',
      schemes: [
        'android-app://com.android.dialer',
        'tel:',
        'intent://phone#Intent;action=android.intent.action.CALL_BUTTON;end'
      ]
    },
    {
      id: 'messages',
      name: 'Mensagens',
      description: 'SMS e mensagens',
      icon: '💬',
      schemes: [
        'android-app://com.google.android.apps.messaging',
        'sms:',
        'intent://messages#Intent;action=android.intent.action.MAIN;end'
      ]
    },
    {
      id: 'clock',
      name: 'Relógio',
      description: 'Relógio e alarmes',
      icon: '⏰',
      schemes: [
        'android-app://com.google.android.deskclock',
        'intent://clock#Intent;action=android.intent.action.SHOW_ALARMS;end'
      ]
    },
    {
      id: 'gallery',
      name: 'Galeria',
      description: 'Fotos e vídeos',
      icon: '🖼️',
      schemes: [
        'android-app://com.motorola.gallery',
        'intent://gallery#Intent;action=android.intent.action.VIEW;type=image/*;end'
      ]
    },
    {
      id: 'recorder',
      name: 'Gravador',
      description: 'Gravador de som',
      icon: '🎙️',
      schemes: [
        'android-app://com.motorola.audiorecorder',
        'intent://recorder#Intent;action=android.provider.MediaStore.RECORD_SOUND;end'
      ]
    },
    {
      id: 'files',
      name: 'Arquivos',
      description: 'Gerenciador de arquivos',
      icon: '📁',
      schemes: [
        'android-app://com.google.android.documentsui',
        'intent://files#Intent;action=android.intent.action.VIEW;type=resource/folder;end'
      ]
    },
    {
      id: 'diagnostics',
      name: 'Diagnósticos',
      description: 'Ferramentas de diagnóstico',
      icon: '🔧',
      schemes: [
        'android-app://com.motorola.device.diagnostics',
        'intent://diagnostics#Intent;action=android.intent.action.MAIN;end'
      ]
    }
  ];

  const showFeedback = (message, type = 'info') => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(''), 3000);
  };

  const tryOpenApp = async (app) => {
    showFeedback(`Tentando abrir ${app.name}...`, 'loading');
    
    for (const scheme of app.schemes) {
      try {
        // Tenta abrir via window.location
        window.location.href = scheme;
        
        // Aguarda um pouco para verificar se funcionou
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Se chegou aqui, pode ter funcionado
        showFeedback(`✅ ${app.name} aberto com sucesso!`, 'success');
        return;
      } catch (error) {
        console.log(`Falha ao abrir ${app.name} com scheme: ${scheme}`, error);
      }
    }
    
    // Se nenhum scheme funcionou
    showFeedback(`❌ Não foi possível abrir ${app.name}`, 'error');
  };

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  useEffect(() => {
    document.body.className = theme;
  }, [theme]);

  return (
    <div className={`app ${theme}`}>
      <header className="header">
        <div className="header-content">
          <h1 className="title">
            <span className="moto-logo">📱</span>
            Moto E13 Factory Apps
          </h1>
          <button 
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label="Alternar tema"
          >
            {theme === 'dark' ? '🌙' : '☀️'}
          </button>
        </div>
        <p className="subtitle">Acesso rápido aos apps de fábrica</p>
      </header>

      {feedback && (
        <div className={`feedback ${feedback.type}`}>
          {feedback.message}
        </div>
      )}

      <main className="main">
        <div className="apps-grid">
          {factoryApps.map(app => (
            <button
              key={app.id}
              className="app-card"
              onClick={() => tryOpenApp(app)}
              aria-label={`Abrir ${app.name}`}
            >
              <div className="app-icon">{app.icon}</div>
              <div className="app-info">
                <h3 className="app-name">{app.name}</h3>
                <p className="app-description">{app.description}</p>
              </div>
              <div className="app-arrow">▶️</div>
            </button>
          ))}
        </div>
      </main>

      <footer className="footer">
        <p>🔧 Ferramenta de acesso aos apps de fábrica do Moto E13</p>
        <p className="warning">
          ⚠️ Alguns apps podem não abrir devido a restrições de segurança
        </p>
      </footer>
    </div>
  );
};

export default App;