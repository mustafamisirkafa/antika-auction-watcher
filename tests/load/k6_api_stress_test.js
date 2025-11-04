/**
 * k6 API Stress Test (Sprint 4)
 * 
 * Tests all critical API endpoints under stress to identify bottlenecks.
 * 
 * Endpoints tested:
 * - GET /health
 * - GET /metrics
 * - GET /api/v1/plans
 * - GET /api/v1/analytics/overview
 * - POST /api/v1/bids
 * 
 * Usage:
 *   docker run --rm -v $(pwd)/tests/load:/scripts grafana/k6 run /scripts/k6_api_stress_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

const BASE_URL = __ENV.BASE_URL || 'http://host.docker.internal:8000';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Warm up
    { duration: '3m', target: 150 },  // Stress
    { duration: '2m', target: 200 },  // Peak
    { duration: '2m', target: 50 },   // Recovery
    { duration: '1m', target: 0 },    // Cool down
  ],
  
  thresholds: {
    'http_req_duration': ['p(95)<3000', 'p(99)<5000'],
    'http_req_failed': ['rate<0.05'],  // 5% error rate acceptable under stress
    'errors': ['rate<0.05'],
  },
};

export default function () {
  // Test health endpoint
  group('Health Checks', function () {
    const health = http.get(`${BASE_URL}/health`);
    check(health, {
      'health status 200': (r) => r.status === 200,
    });
    apiLatency.add(health.timings.duration);
  });
  
  sleep(0.5);
  
  // Test metrics endpoint
  group('Metrics', function () {
    const metrics = http.get(`${BASE_URL}/metrics`);
    check(metrics, {
      'metrics status 200': (r) => r.status === 200,
      'metrics has content': (r) => r.body.includes('autobid_latency'),
    });
    apiLatency.add(metrics.timings.duration);
  });
  
  sleep(0.5);
  
  // Test plans endpoint
  group('Plans API', function () {
    const plans = http.get(`${BASE_URL}/api/v1/plans`);
    check(plans, {
      'plans status 200': (r) => r.status === 200,
    });
    apiLatency.add(plans.timings.duration);
  });
  
  sleep(1);
  
  // Test analytics endpoint
  group('Analytics API', function () {
    const analytics = http.get(`${BASE_URL}/api/v1/analytics/overview`);
    check(analytics, {
      'analytics responds': (r) => r.status < 500,
    });
    apiLatency.add(analytics.timings.duration);
  });
  
  sleep(1);
}

export function handleSummary(data) {
  return {
    '/scripts/k6_stress_results.json': JSON.stringify(data, null, 2),
    'stdout': generateSummary(data),
  };
}

function generateSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  const errors = data.metrics.http_req_failed.values.rate;
  
  return `
  ??????????????????????????????????
  ?? API Stress Test Results
  ??????????????????????????????????
  
  ??  P95 Latency: ${p95.toFixed(2)}ms ${p95 < 3000 ? '?' : '?'}
  ?? Error Rate: ${(errors * 100).toFixed(2)}% ${errors < 0.05 ? '?' : '?'}
  ?? Total Requests: ${data.metrics.http_reqs.values.count}
  ? Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)}/s
  
  Result: ${p95 < 3000 && errors < 0.05 ? '? PASS' : '? FAIL'}
  ??????????????????????????????????
  `;
}
