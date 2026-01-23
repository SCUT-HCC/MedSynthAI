function enableDevMode() {
  let retries = 0;
  const maxRetries = 5;

  function connect() {
    try {
      const socket = new WebSocket('ws://localhost:3000/');
      socket.onopen = function() {
        console.log('WebSocket connection established');
      };
      socket.onerror = function(error) {
        console.error('WebSocket error:', error);
        if (retries < maxRetries) {
          retries++;
          console.log(`Retrying connection (${retries}/${maxRetries})...`);
          setTimeout(connect, 2000); // 2秒后重试
        } else {
          console.error('Max retries reached. Could not establish WebSocket connection.');
        }
      };
      socket.onclose = function(event) {
        console.log('WebSocket connection closed', event);
        if (retries < maxRetries) {
          retries++;
          console.log(`Retrying connection (${retries}/${maxRetries})...`);
          setTimeout(connect, 2000); // 2秒后重试
        } else {
          console.error('Max retries reached. Could not establish WebSocket connection.');
        }
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      if (retries < maxRetries) {
        retries++;
        console.log(`Retrying connection (${retries}/${maxRetries})...`);
        setTimeout(connect, 2000); // 2秒后重试
      } else {
        console.error('Max retries reached. Could not establish WebSocket connection.');
      }
    }
  }

  connect();
}

function handleDeprecationWarnings() {
  const originalWarn = console.warn;
  console.warn = function(message, ...args) {
    if (message.includes('-ms-high-contrast-adjust is in the process of being deprecated')) {
      // 处理弃用警告
      console.log('Deprecation warning:', message);
    } else {
      originalWarn.apply(console, [message, ...args]);
    }
  };
}

handleDeprecationWarnings();
