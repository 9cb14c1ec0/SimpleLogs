/**
 * SimpleLogs TypeScript/JavaScript Client
 *
 * Usage:
 *   import { SimpleLogger } from './simplelogs';
 *
 *   const logger = new SimpleLogger('http://localhost', 'your-api-key', 'my-app');
 *   logger.info('User logged in', { userId: 123 });
 *   logger.error('Payment failed', { orderId: 456, amount: 99.99 });
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'fatal';

interface LogEntry {
  level: LogLevel;
  message: string;
  metadata?: Record<string, unknown>;
  source?: string;
  timestamp?: string;
}

export class SimpleLogger {
  private url: string;
  private headers: Record<string, string>;
  private source?: string;

  constructor(baseUrl: string, apiKey: string, source?: string) {
    this.url = `${baseUrl}/api/v1/ingest`;
    this.headers = {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    };
    this.source = source;
  }

  private async send(level: LogLevel, message: string, metadata?: Record<string, unknown>): Promise<void> {
    const payload: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
    };

    if (metadata) payload.metadata = metadata;
    if (this.source) payload.source = this.source;

    try {
      await fetch(this.url, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(payload),
      });
    } catch {
      // Fire and forget
    }
  }

  debug(message: string, metadata?: Record<string, unknown>): void {
    this.send('debug', message, metadata);
  }

  info(message: string, metadata?: Record<string, unknown>): void {
    this.send('info', message, metadata);
  }

  warn(message: string, metadata?: Record<string, unknown>): void {
    this.send('warn', message, metadata);
  }

  error(message: string, metadata?: Record<string, unknown>): void {
    this.send('error', message, metadata);
  }

  fatal(message: string, metadata?: Record<string, unknown>): void {
    this.send('fatal', message, metadata);
  }

  async batch(logs: LogEntry[]): Promise<void> {
    try {
      await fetch(`${this.url}/batch`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ logs }),
      });
    } catch {
      // Fire and forget
    }
  }
}

// Default export for convenience
export default SimpleLogger;
