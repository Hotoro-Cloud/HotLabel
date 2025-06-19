 # HotLabel Headless Stress Test

This directory contains the headless stress test setup for the HotLabel system, designed to run in browserless VMs or environments without GUI access.

## Overview

The headless stress test simulates real user interactions with the HotLabel system using a headless browser service (browserless.io or similar). It tests the entire system from a client SDK perspective, including:

- Task creation and assignment
- User session management
- Task completion through the SDK
- Consensus calculation
- System performance under load

## Architecture

```
[Headless Stress Test] → [Browserless Service] → [Sample Site] → [HotLabel SDK] → [HotLabel Services]
```

## Prerequisites

### Option 1: Local Development (with Docker)
- Docker and Docker Compose
- Python 3.8+
- All HotLabel services running

### Option 2: Cloud/VM Environment
- Python 3.8+
- Access to browserless.io or similar headless browser service
- Network access to HotLabel services

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements-headless-stress-test.txt

# Run setup script
python scripts/setup_headless_stress_test.py
```

### 2. Run Stress Test

```bash
# Basic test
python scripts/stress_test_client_sdk_headless.py

# Custom parameters
python scripts/stress_test_client_sdk_headless.py \
    --iterations 20 \
    --concurrent 5 \
    --tasks-per-session 2 \
    --browserless-url ws://localhost:3000
```

### 3. Using Docker Compose

```bash
# Start all services including browserless
docker-compose -f docker-compose-headless.yml up -d

# Run stress test
docker-compose -f docker-compose-headless.yml run headless-stress-test \
    python scripts/stress_test_client_sdk_headless.py \
    --iterations 10 \
    --concurrent 2
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BROWSERLESS_URL` | Browserless service URL | `ws://localhost:3000` |
| `KONG_URL` | Kong API Gateway URL | `http://localhost:8000` |
| `SAMPLE_SITE_URL` | Sample site URL | `http://localhost:5001` |

### Browserless Options

#### Local Browserless (Docker)
```bash
# Start browserless locally
docker run -d \
    --name browserless-chrome \
    -p 3000:3000 \
    -e MAX_CONCURRENT_SESSIONS=10 \
    browserless/chrome:latest
```

#### Browserless.io Cloud
```bash
# Use browserless.io cloud service
python scripts/stress_test_client_sdk_headless.py \
    --browserless-url wss://chrome.browserless.io?token=YOUR_API_KEY
```

#### Custom Browserless Service
```bash
# Use any WebSocket-compatible browserless service
python scripts/stress_test_client_sdk_headless.py \
    --browserless-url ws://your-browserless-service:3000
```

## Test Scenarios

The headless stress test creates three types of tasks to test different consensus scenarios:

1. **Positive Consensus**: Tasks designed to reach positive consensus
2. **Negative Consensus**: Tasks designed to reach negative consensus  
3. **Ambiguous Consensus**: Tasks designed to create split consensus

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--iterations` | Number of sessions to run | 10 |
| `--concurrent` | Number of concurrent sessions | 2 |
| `--tasks-per-session` | Tasks per session | 1 |
| `--browserless-url` | Browserless service URL | `ws://localhost:3000` |

## Output

### Console Output
- Real-time progress updates
- Session completion status
- Error reporting
- Final metrics summary

### Results File
Results are saved to `headless_stress_test_results_YYYYMMDD_HHMMSS.json` containing:

```json
{
  "test_config": {
    "iterations": 10,
    "concurrent": 2,
    "tasks_per_session": 1,
    "browserless_url": "ws://localhost:3000"
  },
  "test_duration": "0:05:30",
  "system_metrics": [...],
  "test_results": [...],
  "provider_id": "...",
  "task_ids": [...]
}
```

## Performance Tuning

### Browserless Configuration

```yaml
# docker-compose-headless.yml
browserless:
  environment:
    - MAX_CONCURRENT_SESSIONS=20
    - CONNECTION_TIMEOUT=60000
    - MAX_QUEUE_LENGTH=20
    - PREBOOT_CHROME=true
    - KEEP_ALIVE=true
```

### Stress Test Parameters

```bash
# High load test
python scripts/stress_test_client_sdk_headless.py \
    --iterations 100 \
    --concurrent 10 \
    --tasks-per-session 3

# Long-running test
python scripts/stress_test_client_sdk_headless.py \
    --iterations 1000 \
    --concurrent 5 \
    --tasks-per-session 1
```

## Troubleshooting

### Common Issues

1. **Browserless Connection Failed**
   ```bash
   # Check browserless status
   curl http://localhost:3000/json/version
   
   # Restart browserless
   docker restart browserless-chrome
   ```

2. **HotLabel Services Not Responding**
   ```bash
   # Check service health
   curl http://localhost:8000/status
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

3. **Sample Site Not Accessible**
   ```bash
   # Check sample site
   curl http://localhost:5001
   
   # Ensure sample site is running
   docker-compose -f docker-compose-local.yml up samplesite
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python scripts/stress_test_client_sdk_headless.py
```

### Manual Testing

```bash
# Test browserless connection
python -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
options = Options()
options.add_experimental_option('debuggerAddress', 'localhost:3000')
driver = webdriver.Chrome(options=options)
driver.get('https://httpbin.org/ip')
print(driver.title)
driver.quit()
"
```

## Monitoring

### Real-time Monitoring
- Check browserless dashboard: `http://localhost:3000`
- Monitor HotLabel services: `http://localhost:8000/status`
- View Grafana dashboards: `http://localhost:3000`

### Metrics Collection
The stress test collects:
- Response times
- Task completion rates
- Error rates
- Consensus achievement rates
- System performance metrics

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Headless Stress Test
on: [push, pull_request]

jobs:
  stress-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements-headless-stress-test.txt
      - name: Start services
        run: |
          docker-compose -f docker-compose-headless.yml up -d
      - name: Wait for services
        run: |
          sleep 30
      - name: Run stress test
        run: |
          python scripts/stress_test_client_sdk_headless.py \
            --iterations 10 \
            --concurrent 2
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: stress-test-results
          path: headless_stress_test_results_*.json
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Network Access**: Ensure proper firewall rules for browserless service
3. **Resource Limits**: Set appropriate limits to prevent resource exhaustion
4. **Data Privacy**: Ensure test data doesn't contain sensitive information

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `headless_stress_test_results_*.json`
3. Enable debug mode for detailed logging
4. Check browserless service documentation

## Contributing

To contribute to the headless stress test:

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test with different browserless services
5. Validate performance improvements