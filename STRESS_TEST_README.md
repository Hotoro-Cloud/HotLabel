# HotLabel System Stress Test - Client SDK Perspective

This directory contains a comprehensive stress testing system for the HotLabel platform that simulates real-world usage from the client SDK perspective.

## Overview

The stress test system performs end-to-end testing of the entire HotLabel platform by:

1. **Registering a single publisher** at the beginning
2. **Creating multiple VQA tasks** with different scenarios (living room, fashion, ambiguous)
3. **Using webdriver automation** to access the sample site at `localhost:5001`
4. **Completing tasks through the client SDK** with new sessions each time
5. **Simulating real user behaviors** with random delays and interactions
6. **Monitoring system performance** and recording comprehensive metrics
7. **Testing consensus calculation** and task lifecycle completion

## Prerequisites

### System Requirements
- Python 3.8+
- Chrome browser installed
- ChromeDriver (automatically managed by Selenium)
- Docker and Docker Compose

### Services Running
All HotLabel services must be running:
```bash
cd hotlabel-infra
docker-compose -f docker-compose-local.yml up -d
```

## Quick Start

### 1. Setup Environment
```bash
cd hotlabel-infra
python scripts/setup_stress_test.py
```

This script will:
- Check if all services are running
- Install required Python dependencies
- Verify Chrome webdriver setup
- Run a quick connectivity test

### 2. Run Basic Stress Test
```bash
python scripts/stress_test_client_sdk.py
```

Default configuration:
- 50 sessions
- 5 concurrent sessions
- 3 tasks per session

### 3. Run Custom Stress Test
```bash
python scripts/stress_test_client_sdk.py \
  --iterations 100 \
  --concurrent 10 \
  --tasks-per-session 5
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--iterations` | 50 | Number of sessions to run |
| `--concurrent` | 5 | Number of concurrent sessions |
| `--tasks-per-session` | 3 | Number of tasks per session |
| `--headless` | True | Run browser in headless mode |

## Test Scenarios

The stress test creates three different VQA task scenarios:

### 1. VQA Living Room
- **Image**: Living room scene with various objects
- **Question**: "is there anything else that is the same shape as the tiny blue rubber thing?"
- **Expected Consensus**: High agreement on "True" (75% True, 25% False)

### 2. VQA Fashion
- **Image**: Fashion items and accessories
- **Question**: "is there a tiny red object made of the same material as the large gray bag?"
- **Expected Consensus**: Mixed agreement pattern

### 3. VQA Ambiguous
- **Image**: Scene with ambiguous objects
- **Question**: "is there a green object that is both soft and metallic?"
- **Expected Consensus**: Low agreement (no clear consensus)

## Test Flow

### 1. Environment Setup
- Register a stress test provider
- Register a stress test publisher
- Create VQA tasks for each scenario

### 2. Session Execution
For each session:
- Create new webdriver instance
- Navigate to sample site (`localhost:5001`)
- Complete quiz questions (simulating user interaction)
- Submit quiz and wait for results
- Record metrics and timing

### 3. Concurrent Processing
- Multiple sessions run concurrently using ThreadPoolExecutor
- Each session is independent with its own webdriver instance
- Results are collected thread-safely

### 4. Metrics Collection
- Response times for each task completion
- Success/failure rates
- Task status tracking
- System performance metrics

## Output and Results

### Console Output
The test provides real-time progress updates:
```
================================================================================
 Starting HotLabel System Stress Test 
================================================================================

--- Setting up test environment ---
Provider registered: 12345678-1234-1234-1234-123456789abc
Publisher registered: 87654321-4321-4321-4321-cba987654321

--- Creating test tasks ---
Created task task-001 for scenario vqa_living_room
Created task task-002 for scenario vqa_fashion
Created task task-003 for scenario vqa_ambiguous

Session 1, Task 1: Completing vqa_living_room
Successfully completed task task-001 via webdriver
Completed session 1
```

### Results File
A JSON file is generated with comprehensive results:
```json
{
  "test_config": {
    "iterations": 50,
    "concurrent": 5,
    "tasks_per_session": 3
  },
  "test_duration": "0:05:23.456789",
  "system_metrics": [...],
  "test_results": [...],
  "provider_id": "12345678-1234-1234-1234-123456789abc",
  "publisher_id": "87654321-4321-4321-4321-cba987654321",
  "task_ids": ["task-001", "task-002", "task-003"]
}
```

### Final Summary
```
================================================================================
 Stress Test Results 
================================================================================
Test Duration: 0:05:23.456789
Total Sessions: 50
Total Tasks Completed: 147
Total Errors: 3
Success Rate: 98.00%
Average Response Time: 2345.67ms
Average Task Completion Time: 1890.45ms
Tasks Completed: 2
Tasks In Progress: 1
Tasks Failed: 0

Results saved to: stress_test_results_20241201_143022.json
```

## Monitoring and Debugging

### Service Health Checks
The setup script checks all required services:
- Kong API Gateway (port 8000)
- Tasks Service (port 8002)
- Publishers Service (port 8004)
- QA Service (port 8003)
- Users Service (port 8005)
- Sample Site (port 5001)

### Error Handling
The test includes comprehensive error handling:
- WebDriver failures (timeouts, element not found)
- API connectivity issues
- Service unavailability
- Task completion failures

### Logging
All operations are logged with timestamps and session IDs for debugging.

## Performance Considerations

### Resource Usage
- **Memory**: Each webdriver instance uses ~50-100MB
- **CPU**: Browser automation is CPU-intensive
- **Network**: Multiple concurrent API calls

### Scaling Guidelines
- **Light Load**: 10-20 concurrent sessions
- **Medium Load**: 20-50 concurrent sessions
- **Heavy Load**: 50+ concurrent sessions (monitor system resources)

### Optimization Tips
- Use headless mode for faster execution
- Adjust delays between tasks based on system performance
- Monitor system resources during testing
- Consider running on dedicated test machines for large-scale tests

## Troubleshooting

### Common Issues

#### 1. Chrome WebDriver Issues
```bash
# Install ChromeDriver manually if needed
brew install chromedriver  # macOS
sudo apt-get install chromium-chromedriver  # Ubuntu
```

#### 2. Service Connection Issues
```bash
# Check if services are running
docker-compose -f docker-compose-local.yml ps

# Restart services if needed
docker-compose -f docker-compose-local.yml restart
```

#### 3. Sample Site Not Accessible
```bash
# Check if sample site is running
curl http://localhost:5001

# Start sample site if needed
cd hotlabel-samplesite
docker-compose up -d
```

#### 4. Memory Issues
- Reduce concurrent sessions
- Increase system memory
- Use headless mode
- Close other applications

### Debug Mode
For debugging, you can run with visible browser:
```bash
python scripts/stress_test_client_sdk.py --headless false
```

## Integration with CI/CD

The stress test can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Stress Test
  run: |
    cd hotlabel-infra
    python scripts/setup_stress_test.py
    python scripts/stress_test_client_sdk.py --iterations 20 --concurrent 3
```

## Contributing

To extend the stress test:

1. **Add new scenarios**: Extend `TaskScenario` enum and `create_task_data_for_scenario()`
2. **Modify user behavior**: Update `complete_quiz_questions()` method
3. **Add metrics**: Extend `SystemMetrics` dataclass
4. **Customize test flow**: Modify `run_single_session()` method

## Files Structure

```
hotlabel-infra/
├── scripts/
│   ├── stress_test_client_sdk.py      # Main stress test script
│   └── setup_stress_test.py           # Setup and validation script
├── requirements-stress-test.txt        # Python dependencies
└── STRESS_TEST_README.md              # This documentation
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the console output for error messages
3. Examine the generated results file
4. Check service logs: `docker-compose -f docker-compose-local.yml logs` 