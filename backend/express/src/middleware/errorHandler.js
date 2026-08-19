// src/middleware/errorHandler.js
export function errorHandler(err, req, res, next) {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
      request_id: req.headers['x-request-id'] || 'unknown'
    }
  });
}
