/**
 * Express.js integration example for SimpleLogs
 *
 * Run with: npx ts-node express_example.ts
 */

import express, { Request, Response, NextFunction } from 'express';
import { SimpleLogger } from './simplelogs';

const app = express();
app.use(express.json());

// Initialize the logger
const logger = new SimpleLogger(
  'http://localhost',
  'YOUR_API_KEY',
  'express-app'
);

// Middleware to log all requests
app.use((req: Request, res: Response, next: NextFunction) => {
  logger.info(`${req.method} ${req.path}`, {
    method: req.method,
    path: req.path,
    ip: req.ip,
    userAgent: req.get('user-agent'),
  });

  // Log response when finished
  res.on('finish', () => {
    if (res.statusCode >= 400) {
      logger.warn(`Request failed with ${res.statusCode}`, {
        path: req.path,
        statusCode: res.statusCode,
      });
    }
  });

  next();
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  logger.error(`Unhandled exception: ${err.message}`, {
    path: req.path,
    method: req.method,
    errorType: err.name,
    stack: err.stack,
  });

  res.status(500).json({ error: 'Internal server error' });
});

// Routes
app.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Hello, World!' });
});

app.get('/users/:id', (req: Request, res: Response) => {
  const userId = parseInt(req.params.id);

  logger.debug(`Fetching user ${userId}`, { userId });

  // Simulate user lookup
  const user = { id: userId, name: 'John Doe' };

  logger.info(`User ${userId} retrieved`, { userId });
  res.json(user);
});

app.post('/orders', (req: Request, res: Response) => {
  const order = req.body;

  logger.info('Order created', {
    userId: order.userId,
    items: order.items?.length || 0,
    total: order.total,
  });

  res.json({ orderId: 12345, status: 'created' });
});

app.post('/login', (req: Request, res: Response) => {
  const { email } = req.body;

  // Simulate login
  const success = email !== 'bad@example.com';

  if (success) {
    logger.info('User logged in', { email });
    res.json({ status: 'success', token: 'abc123' });
  } else {
    logger.warn('Login failed', { email, reason: 'Invalid credentials' });
    res.status(401).json({ error: 'Invalid credentials' });
  }
});

app.get('/error', (req: Request, res: Response) => {
  logger.error('Intentional error triggered', { endpoint: '/error' });
  throw new Error('Something went wrong');
});

const PORT = 3000;
app.listen(PORT, () => {
  logger.info(`Server started on port ${PORT}`, { port: PORT });
  console.log(`Server running on http://localhost:${PORT}`);
});
