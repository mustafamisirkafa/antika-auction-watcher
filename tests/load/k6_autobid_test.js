/**
 * k6 Load Test for AutoBid System (Sprint 4)
 * 
 * Tests the AutoBid endpoint under realistic load to validate:
 * - P95 latency < 3s (SLA requirement)
 * - Error rate < 1%
 * - System stability under sustained load
 * 
 * Usage:
 *   docker run --rm -v $(pwd)/tests/load:/scripts grafana/k6 run /scripts/k6_autobid_test.js
 * 
 * Environment:
 *   BASE_URL - Target API URL (default: http://host.docker.internal:8000)
 *   VUS - Virtual users (default: 100)
 *   DURATION - Test duration (default: 10m)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const bidLatency = new Trend('bid_latency');
const successfulBids = new Counter('successful_bids');
const failedBids = new Counter('failed_bids');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://host.docker.internal:8000';
const VUS = __ENV.VUS || 100;
const DURATION = __ENV.DURATION || '10m';

// Test configuration
export const options = {
  stages: [
    // Ramp-up: 0 ? 100 VUs over 2 minutes
    { duration: '2m', target: VUS },
    
    // Steady state: 100 VUs for 6 minutes
    { duration: '6m', target: VUS },
    
    // Ramp-down: 100 ? 0 VUs over 2 minutes
    { duration: '2m', target: 0 },
  ],
  
  thresholds: {
    // SLA requirement: P95 latency < 3000ms
    'http_req_duration': ['p(95)<3000'],
    
    // Error rate < 1%
    'http_req_failed': ['rate<0.01'],
    
    // Custom thresholds
    'bid_latency': ['p(95)<3000', 'p(99)<5000'],
    'errors': ['rate<0.01'],
  },
  
  // Output results to JSON for Grafana import
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// Test data generator
function generateBidPayload() {
  const categories = ['ceramics', 'coins', 'paintings', 'furniture', 'textiles'];
  const auctionId = `A${Math.floor(Math.random() * 1000)}`;
  const itemId = `I${Math.floor(Math.random() * 5000)}`;
  
  return {
    auction_id: auctionId,
    item_id: itemId,
    amount: Math.floor(Math.random() * 5000) + 100,
    category: categories[Math.floor(Math.random() * categories.length)],
    max_bid: Math.floor(Math.random() * 10000) + 1000,
    confidence_threshold: 0.7,
  };
}

// Authentication token (mock for testing)
const AUTH_TOKEN = 'test-token-' + Math.random().toString(36).substr(2, 9);

export default function () {
  const payload = JSON.stringify(generateBidPayload());
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${AUTH_TOKEN}`,
    },
    tags: {
      name: 'AutoBidRequest',
    },
  };
  
  // Execute bid request
  const response = http.post(`${BASE_URL}/api/v1/bids`, payload, params);
  
  // Record custom metrics
  bidLatency.add(response.timings.duration);
  
  // Check response
  const success = check(response, {
    'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
    'status is not 5xx': (r) => r.status < 500,
    'response time < 3000ms': (r) => r.timings.duration < 3000,
    'response has body': (r) => r.body.length > 0,
  });
  
  if (success) {
    successfulBids.add(1);
  } else {
    failedBids.add(1);
    errorRate.add(1);
    console.error(`Request failed: ${response.status} - ${response.body}`);
  }
  
  // Error tracking
  if (!success) {
    errorRate.add(1);
  }
  
  // Random think time between requests (0.5s to 2s)
  sleep(Math.random() * 1.5 + 0.5);
}

// Setup function (runs once before test)
export function setup() {
  console.log(`?? Starting AutoBid load test`);
  console.log(`   Target: ${BASE_URL}`);
  console.log(`   Virtual Users: ${VUS}`);
  console.log(`   Duration: ${DURATION}`);
  console.log(`   SLA: P95 < 3000ms, Error rate < 1%`);
  
  // Health check
  const healthCheck = http.get(`${BASE_URL}/health`);
  if (healthCheck.status !== 200) {
    console.error(`? Backend health check failed: ${healthCheck.status}`);
    throw new Error('Backend not healthy, aborting test');
  }
  
  console.log(`? Backend is healthy, starting load test...`);
  return { startTime: new Date().toISOString() };
}

// Teardown function (runs once after test)
export function teardown(data) {
  console.log(`\n?? Load Test Summary`);
  console.log(`   Started: ${data.startTime}`);
  console.log(`   Ended: ${new Date().toISOString()}`);
  console.log(`   Target: ${BASE_URL}`);
}

// Custom summary handler
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    test_config: {
      base_url: BASE_URL,
      virtual_users: VUS,
      duration: DURATION,
    },
    metrics: {
      http_req_duration: {
        avg: data.metrics.http_req_duration.values.avg,
        min: data.metrics.http_req_duration.values.min,
        max: data.metrics.http_req_duration.values.max,
        p95: data.metrics.http_req_duration.values['p(95)'],
        p99: data.metrics.http_req_duration.values['p(99)'],
      },
      http_req_failed: {
        rate: data.metrics.http_req_failed.values.rate,
        count: data.metrics.http_req_failed.values.count,
      },
      http_reqs: {
        count: data.metrics.http_reqs.values.count,
        rate: data.metrics.http_reqs.values.rate,
      },
      successful_bids: data.metrics.successful_bids?.values.count || 0,
      failed_bids: data.metrics.failed_bids?.values.count || 0,
    },
    thresholds: data.metrics.http_req_duration.thresholds,
  };
  
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    '/scripts/k6_results.json': JSON.stringify(summary, null, 2),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const colors = options.enableColors;
  
  let output = '\n';
  output += indent + '??????????????????????????????????????????\n';
  output += indent + '?? k6 Load Test Results\n';
  output += indent + '??????????????????????????????????????????\n\n';
  
  const duration = data.metrics.http_req_duration.values;
  const p95 = duration['p(95)'];
  const p95Pass = p95 < 3000;
  
  output += indent + `??  Latency:\n`;
  output += indent + `   P50: ${duration.med.toFixed(2)}ms\n`;
  output += indent + `   P95: ${p95.toFixed(2)}ms ${p95Pass ? '?' : '?'} (SLA: <3000ms)\n`;
  output += indent + `   P99: ${duration['p(99)'].toFixed(2)}ms\n`;
  output += indent + `   Max: ${duration.max.toFixed(2)}ms\n\n`;
  
  const errorRate = data.metrics.http_req_failed.values.rate;
  const errorPass = errorRate < 0.01;
  
  output += indent + `?? Errors:\n`;
  output += indent + `   Rate: ${(errorRate * 100).toFixed(2)}% ${errorPass ? '?' : '?'} (SLA: <1%)\n`;
  output += indent + `   Count: ${data.metrics.http_req_failed.values.count}\n\n`;
  
  output += indent + `?? Requests:\n`;
  output += indent + `   Total: ${data.metrics.http_reqs.values.count}\n`;
  output += indent + `   Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)}/s\n\n`;
  
  const allPassed = p95Pass && errorPass;
  output += indent + `??????????????????????????????????????????\n`;
  output += indent + `Result: ${allPassed ? '? PASS' : '? FAIL'}\n`;
  output += indent + '??????????????????????????????????????????\n';
  
  return output;
}
