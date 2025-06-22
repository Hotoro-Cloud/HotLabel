# TII All Categories Task Puller

This script extends the original `pull_TII_random.py` to fetch random tasks from all available TII (Technology Innovation Institute) categories and create them in the Hotlabel tasks service.

## Features

- **Comprehensive Coverage**: Fetches tasks from all TII categories, types, languages, topics, and complexity levels
- **Smart Filtering**: Uses intelligent filter combinations to maximize task diversity
- **Rate Limiting**: Built-in delays to avoid overwhelming the TII API
- **Dry Run Mode**: Test the script without actually creating tasks
- **Detailed Logging**: Comprehensive logging and task summaries
- **Error Handling**: Robust error handling for API failures

## TII API Categories Covered

### Categories
- **vqa**: Visual Question Analysis related Tasks

### Task Types
- **true-false**: Tasks with True or False solution
- **numeric**: Tasks with a number as the solution  
- **mcq**: Tasks with a short answer solution

### Languages
- **en**: English
- **ar**: Arabic

### Topics
- **animals**: Animal-related topics
- **construction-site**: Construction-related topics
- **fashion**: Fashion-related topics
- **garage-workshop**: Workshop-related topics
- **kitchen**: Kitchen-related topics
- **living-room**: Furniture and living room topics
- **medical-field**: Medical field topics
- **music**: Music and musical instruments
- **office**: Office environment topics
- **school**: School and school supplies
- **uae**: UAE culture and heritage
- **underwater**: Underwater environments

### Complexity Levels
- **1**: Least complex
- **2**: Low complexity
- **3**: Medium complexity
- **4**: Most complex

## Usage

### Basic Usage
```bash
# Fetch and create 50 tasks (default)
python pull_TII_all_categories.py

# Fetch and create 10 tasks
python pull_TII_all_categories.py --max-tasks 10

# Dry run - only fetch and display, don't create tasks
python pull_TII_all_categories.py --dry-run

# Use custom API key
python pull_TII_all_categories.py --api-key YOUR_API_KEY

# Enable SSL verification
python pull_TII_all_categories.py --verify

# Use custom provider ID
python pull_TII_all_categories.py --provider-id YOUR_PROVIDER_ID

# Custom delay between requests (default: 1.0 seconds)
python pull_TII_all_categories.py --delay 2.0
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--api-key` | TII API key for authentication | Uses default key in script |
| `--verify` | Enable SSL certificate verification | Disabled |
| `--dry-run` | Only fetch and display tasks, don't submit | False |
| `--max-tasks` | Maximum number of tasks to fetch | 50 |
| `--provider-id` | Provider ID for creating tasks | Uses default in script |
| `--delay` | Delay between API requests in seconds | 1.0 |

## Configuration

### API Keys
The script uses two API keys:
1. **TII API Key**: For fetching tasks from TII (`API_KEY`)
2. **Hotlabel Tasks API Key**: For creating tasks in Hotlabel (`TASKS_API_KEY`)

### Endpoints
- **TII API**: `https://crowdlabel.tii.ae/api/2025.2/tasks/pick`
- **Hotlabel Tasks**: `http://localhost:8000/api/v1/tasks` (via Kong gateway)

## Task Transformation

The script transforms TII tasks into Hotlabel format:

### TII Task Structure
```json
{
    "id": "<task_id>",
    "category": "vqa",
    "complexity": 1,
    "type": "true-false",
    "topic": "uae",
    "language": "en",
    "content": {
        "image": {
            "filename": "<image_filename>",
            "url": "<image_url>"
        }
    },
    "task": {
        "text": "This is a question. Pick one of the following answers.",
        "choices": [
            {"key": "a", "value": "True"},
            {"key": "b", "value": "False"}
        ]
    },
    "track_id": "<track_id>"
}
```

### Hotlabel Task Structure
```json
{
    "title": "TII Task: <tii_id>",
    "description": "Task imported from TII with topic: <topic>",
    "provider_id": "<provider_id>",
    "task_type": "<category>",
    "content": {
        "question": "<question_text>",
        "image_url": "<image_url>"  // if available
    },
    "language": "<language>",
    "category": "<category>",
    "complexity_level": <complexity>,
    "options": {
        "tii_id": "<tii_id>",
        "tii_track_id": "<track_id>",
        "tii_task_type": "<type>",
        "tii_topic": "<topic>",
        "choices": "<choices>"
    },
    "time_estimate_seconds": 300,
    "tags": ["tii", "<category>", "<topic>", "<type>", "<language>"],
    "golden_set": false,
    "expires_at": "<expiration_date>",
    "status": "pending"
}
```

## Filter Combinations

The script generates intelligent filter combinations to maximize task diversity:

1. **Single Filters**: Individual category, type, language, topic, complexity
2. **Common Combinations**: Frequently used combinations like VQA + English
3. **Random Combinations**: Randomly generated combinations for variety

## Error Handling

The script handles various error scenarios:
- **Authentication Errors**: Invalid API keys
- **Network Errors**: Connection issues
- **Rate Limiting**: Built-in delays between requests
- **Missing Tasks**: Graceful handling when no tasks match filters
- **Service Errors**: Hotlabel service failures

## Output

### Console Output
The script provides detailed console output:
- Task details for each fetched task
- Success/failure status for each task creation
- Summary statistics at the end

### Logging
Comprehensive logging includes:
- API request details
- Error messages
- Progress tracking
- Summary information

## Example Output

```
2024-01-15 10:30:00 - __main__ - INFO - Starting TII all categories task pull script
2024-01-15 10:30:00 - __main__ - INFO - Generated 25 filter combinations

--- Task 1 ---
TII ID: tii_12345
Category: vqa
Type: true-false
Language: en
Topic: uae
Complexity: 2
✅ Task created successfully

--- Task 2 ---
TII ID: tii_12346
Category: vqa
Type: mcq
Language: ar
Topic: medical-field
Complexity: 3
✅ Task created successfully

========== TASK SUMMARY ==========
Total tasks fetched from TII: 20
Total tasks created in Hotlabel: 18

Tasks by category:
  vqa: 20
==================================
```

## Development Rules Compliance

This script follows the Hotlabel development rules:
- Uses the local development environment configuration
- Compatible with the Kong gateway setup
- Follows the established task creation patterns
- Uses the same API keys and endpoints as other scripts

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your TII API key is correct
   - Check that the Hotlabel tasks API key is valid

2. **No Tasks Found**
   - Some filter combinations may not have available tasks
   - Try different combinations or increase the max-tasks limit

3. **Service Unavailable**
   - Ensure the Hotlabel services are running
   - Check that Kong gateway is accessible at `http://localhost:8000`

4. **Rate Limiting**
   - Increase the delay between requests using `--delay`
   - The TII API may have rate limits

### Debug Mode
For debugging, use the `--dry-run` flag to see what tasks would be created without actually creating them. 