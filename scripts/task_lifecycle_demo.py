#!/usr/bin/env python3
"""
Dynamic Task Lifecycle Demo

This script demonstrates the complete lifecycle of tasks in the Hotlabel platform:
1. Dynamically discovers all available task types and their options from the database
2. Tests all task types with various consensus scenarios
3. Uses actual task options instead of hardcoded values
4. Ensures comprehensive coverage of all possible task configurations
5. Adapts to the actual content and structure of tasks in the database
"""

import requests
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
import sys
import random
import os
import subprocess
from enum import Enum
from collections import defaultdict

# Configuration
KONG_URL = "http://localhost:8000"  # API Gateway URL
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
PUBLISHERS_API_URL = f"{KONG_URL}/api/v1/publishers"
QA_API_URL = f"{KONG_URL}/api/v1/consensus"
SESSIONS_API_URL = f"{KONG_URL}/api/v1/sessions"

# Direct service URLs (if needed for endpoints not exposed through Kong)
TASKS_SERVICE_URL = "http://localhost:8002"
PUBLISHERS_SERVICE_URL = "http://localhost:8004"
QA_SERVICE_URL = "http://localhost:8003"
USERS_SERVICE_URL = "http://localhost:8005"

# QA Service endpoints
VALIDATION_URL = f"{QA_SERVICE_URL}/api/v1/validation"
METRICS_URL = f"{QA_SERVICE_URL}/api/v1/metrics"
QA_API_KEY = "test_api_key_qa_service"  # QA service API key

# Internal service headers
INTERNAL_HEADERS = {"X-Internal-Service": "true"}

class ConsensusScenario(Enum):
    HIGH_AGREEMENT = "high_agreement"      # 80% choose same option
    MEDIUM_AGREEMENT = "medium_agreement"  # 60% choose same option
    LOW_AGREEMENT = "low_agreement"        # 50% split
    HIGH_CONFIDENCE = "high_confidence"    # All high confidence, mixed answers
    MIXED_CONFIDENCE = "mixed_confidence"  # Mixed confidence levels
    EDGE_CASE = "edge_case"                # Very low confidence
    RANDOM_DISTRIBUTION = "random_distribution"  # Random distribution across all options

def print_header(title: str) -> None:
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_step(step: str) -> None:
    """Print a step in the process"""
    print(f"\n--- {step} ---")

def print_response(response: requests.Response, title: str) -> None:
    """Print API response in a readable format"""
    print(f"\n=== {title} ===")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(f"Raw response text: {response.text}")
    print("-" * 50)

class DynamicTaskLifecycle:
    """Class to manage dynamic task lifecycle demonstration"""
    
    def __init__(self):
        self.tasks = []  # All available tasks
        self.task_types = set()  # Set of all task types found
        self.task_categories = set()  # Set of all task categories found
        self.task_options = {}  # Map task_id to available options
        self.publisher_ids = []
        self.publisher_api_keys = []
        self.sessions = {}  # Map publisher_id to list of session IDs
        self.session_data = {}  # Map session_id to session metadata
        self.task_scenarios = {}  # Map task_id to scenario type
        self.scenario_results = {}  # Map scenario to results for analysis
        
    def discover_tasks_and_options(self) -> Dict[str, Any]:
        """Discover all available tasks and their options"""
        print_step("STEP 1: Discover all available tasks and their options")
        
        # Get all tasks from the tasks service using internal headers
        response = requests.get(f"{TASKS_SERVICE_URL}/api/v1/tasks", headers=INTERNAL_HEADERS)
        print_response(response, "Get All Tasks")
        
        if response.status_code >= 300:
            print("ERROR: Failed to get tasks")
            sys.exit(1)
            
        all_tasks = response.json().get("items", [])
        print(f"Found {len(all_tasks)} total tasks in the database")
        
        # Analyze all tasks to discover types, categories, and options
        for task in all_tasks:
            task_id = task["id"]
            task_type = task.get("task_type", "unknown")
            category = task.get("category", "unknown")
            
            self.task_types.add(task_type)
            self.task_categories.add(category)
            
            # Extract options from task content
            options = self._extract_task_options(task)
            if options:
                self.task_options[task_id] = options
                self.tasks.append(task)
        
        # Print discovery results
        print(f"\nDiscovered {len(self.task_types)} task types: {sorted(self.task_types)}")
        print(f"Discovered {len(self.task_categories)} categories: {sorted(self.task_categories)}")
        print(f"Found {len(self.tasks)} tasks with extractable options")
        
        # Show sample of task options by type
        print("\nSample task options by type:")
        for task_type in sorted(self.task_types):
            type_tasks = [t for t in self.tasks if t.get("task_type") == task_type]
            if type_tasks:
                sample_task = type_tasks[0]
                sample_options = self.task_options.get(sample_task["id"], [])
                print(f"  {task_type}: {sample_options}")
        
        return {
            "total_tasks": len(all_tasks),
            "tasks_with_options": len(self.tasks),
            "task_types": sorted(self.task_types),
            "categories": sorted(self.task_categories)
        }

    def _extract_task_options(self, task: Dict[str, Any]) -> List[str]:
        """Extract available options from task content"""
        options = []
        
        # Check content.options first (most common)
        content = task.get("content", {})
        if isinstance(content, dict):
            content_options = content.get("options", [])
            if isinstance(content_options, list):
                options.extend(content_options)
        
        # Check task.options as fallback
        task_options = task.get("options", [])
        if isinstance(task_options, list):
            options.extend(task_options)
        
        # For true-false tasks, ensure we have True/False options
        if task.get("task_type") == "true-false" and not options:
            options = ["True", "False"]
        
        # For numeric tasks, try to extract from content
        if task.get("task_type") == "numeric" and not options:
            # Look for numeric patterns in content
            if isinstance(content, dict):
                question = content.get("question", "")
                # Try to find numbers in the question or content
                import re
                numbers = re.findall(r'\d+', question)
                if numbers:
                    options = list(set(numbers))  # Remove duplicates
        
        return options

    def select_tasks_for_testing(self, max_tasks_per_type: int = 3) -> List[Dict[str, Any]]:
        """Select a representative set of tasks for testing"""
        print_step(f"STEP 2: Select representative tasks for testing (max {max_tasks_per_type} per type)")
        
        selected_tasks = []
        tasks_by_type = defaultdict(list)
        
        # Group tasks by type
        for task in self.tasks:
            task_type = task.get("task_type", "unknown")
            tasks_by_type[task_type].append(task)
        
        # Select representative tasks from each type
        for task_type, type_tasks in tasks_by_type.items():
            # Sort by status to prioritize ASSIGNED tasks
            type_tasks.sort(key=lambda t: (t.get("status") != "ASSIGNED", t.get("created_at", "")))
            
            # Take up to max_tasks_per_type from each type
            selected_from_type = type_tasks[:max_tasks_per_type]
            selected_tasks.extend(selected_from_type)
            
            print(f"  {task_type}: Selected {len(selected_from_type)} tasks from {len(type_tasks)} available")
        
        print(f"\nTotal selected tasks: {len(selected_tasks)}")
        
        # Assign scenarios to selected tasks
        self._assign_scenarios_to_tasks(selected_tasks)
        
        return selected_tasks

    def _assign_scenarios_to_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Assign consensus scenarios to tasks for comprehensive testing"""
        scenarios = list(ConsensusScenario)
        
        for i, task in enumerate(tasks):
            task_id = task["id"]
            task_type = task.get("task_type", "unknown")
            
            # Cycle through scenarios to ensure all are tested
            scenario = scenarios[i % len(scenarios)]
            self.task_scenarios[task_id] = scenario
            
            print(f"  Task {task_id} ({task_type}): {scenario.value}")

    def register_multiple_publishers(self, count: int = 12) -> List[Dict[str, Any]]:
        """Register multiple publishers"""
        print_step(f"STEP 3: Register {count} publishers")
        
        publishers = []
        for i in range(count):
            publisher_data = {
                "name": f"Demo Publisher {i+1}",
                "email": f"publisher_{i+1}_{uuid.uuid4().hex[:8]}@example.com",
                "website": f"https://example.com/publisher{i+1}",
                "description": f"Demo publisher {i+1} for comprehensive task lifecycle testing"
            }
            
            response = requests.post(PUBLISHERS_API_URL, json=publisher_data)
            if response.status_code >= 300:
                print(f"ERROR: Failed to register publisher {i+1}")
                continue
                
            result = response.json()
            self.publisher_ids.append(result["id"])
            self.publisher_api_keys.append(result["api_key"])
            publishers.append(result)
            
            print(f"Publisher {i+1} registered: {result['id']}")
        
        print(f"Successfully registered {len(publishers)} publishers")
        return publishers

    def create_sessions_for_publishers(self, sessions_per_publisher: int = 2) -> Dict[str, List[str]]:
        """Create sessions for publishers"""
        print_step(f"STEP 4: Create {sessions_per_publisher} sessions per publisher")
        
        for i, publisher_id in enumerate(self.publisher_ids):
            publisher_sessions = []
            for j in range(sessions_per_publisher):
                session_data = {
                    "publisher_id": publisher_id,
                    "language": "en",
                    "consent_given": True,
                    "browser_fingerprint": f"fingerprint_{publisher_id}_{j}"
                }
                
                response = requests.post(f"{USERS_SERVICE_URL}/api/v1/sessions", json=session_data)
                if response.status_code >= 300:
                    print(f"ERROR: Failed to create session {j+1} for publisher {i+1}")
                    continue
                    
                session = response.json()
                session_id = session["id"]
                publisher_sessions.append(session_id)
                self.session_data[session_id] = session
                
                print(f"Created session {session_id} for publisher {publisher_id}")
            
            self.sessions[publisher_id] = publisher_sessions
        
        total_sessions = sum(len(sessions) for sessions in self.sessions.values())
        print(f"Created {total_sessions} sessions across {len(self.publisher_ids)} publishers")
        return self.sessions

    def generate_dynamic_result(self, task: Dict[str, Any], scenario: ConsensusScenario, publisher_index: int) -> Dict[str, Any]:
        """Generate a result based on the scenario and actual task options"""
        task_id = task["id"]
        task_type = task.get("task_type", "unknown")
        options = self.task_options.get(task_id, [])
        
        if not options:
            # Fallback for tasks without extractable options
            if task_type == "true-false":
                options = ["True", "False"]
            elif task_type == "numeric":
                options = ["1", "2", "3", "4"]
            else:
                options = ["option1", "option2", "option3"]
        
        total_publishers = len(self.publisher_ids) * len(next(iter(self.sessions.values())))
        
        if scenario == ConsensusScenario.HIGH_AGREEMENT:
            # 80% choose the first option, 20% choose others
            threshold = int(total_publishers * 0.8)
            if publisher_index < threshold:
                answer = options[0]
                confidence = random.uniform(0.8, 1.0)
            else:
                answer = random.choice(options[1:] if len(options) > 1 else options)
                confidence = random.uniform(0.6, 0.9)
                
        elif scenario == ConsensusScenario.MEDIUM_AGREEMENT:
            # 60% choose the first option, 40% choose others
            threshold = int(total_publishers * 0.6)
            if publisher_index < threshold:
                answer = options[0]
                confidence = random.uniform(0.7, 0.9)
            else:
                answer = random.choice(options[1:] if len(options) > 1 else options)
                confidence = random.uniform(0.7, 0.9)
                
        elif scenario == ConsensusScenario.LOW_AGREEMENT:
            # 50% choose first option, 50% choose others
            threshold = total_publishers // 2
            if publisher_index < threshold:
                answer = options[0]
                confidence = random.uniform(0.6, 0.8)
            else:
                answer = random.choice(options[1:] if len(options) > 1 else options)
                confidence = random.uniform(0.6, 0.8)
                
        elif scenario == ConsensusScenario.HIGH_CONFIDENCE:
            # All high confidence but mixed answers
            answer = random.choice(options)
            confidence = random.uniform(0.9, 1.0)
            
        elif scenario == ConsensusScenario.MIXED_CONFIDENCE:
            # Mixed confidence levels
            answer = random.choice(options)
            if publisher_index < total_publishers // 3:
                confidence = random.uniform(0.9, 1.0)
            elif publisher_index < 2 * total_publishers // 3:
                confidence = random.uniform(0.5, 0.7)
            else:
                confidence = random.uniform(0.3, 0.6)
                
        elif scenario == ConsensusScenario.EDGE_CASE:
            # Very low confidence
            answer = random.choice(options)
            confidence = random.uniform(0.1, 0.3)
            
        else:  # RANDOM_DISTRIBUTION
            # Random distribution across all options
            answer = random.choice(options)
            confidence = random.uniform(0.3, 0.9)
        
        return {
            "answer": answer,
            "confidence": confidence,
            "options_available": options
        }

    def submit_results_for_task(self, task: Dict[str, Any], results_per_session: int = 1) -> List[Dict[str, Any]]:
        """Submit results for a specific task with dynamic options"""
        task_id = task["id"]
        task_type = task.get("task_type", "unknown")
        scenario = self.task_scenarios.get(task_id, ConsensusScenario.RANDOM_DISTRIBUTION)
        
        print_step(f"Submitting results for task {task_id} ({task_type})")
        print(f"Using scenario: {scenario.value}")
        print(f"Available options: {self.task_options.get(task_id, [])}")
        
        submitted_results = []
        publisher_index = 0
        scenario_results = []
        
        for publisher_id, sessions in self.sessions.items():
            for session_id in sessions:
                for submission in range(results_per_session):
                    # Generate result based on scenario and actual task options
                    result_data = self.generate_dynamic_result(task, scenario, publisher_index)
                    
                    # Submit result using the correct endpoint and data format
                    submission_data = {
                        "publisher_id": publisher_id,
                        "session_id": session_id,
                        "result": {
                            "label": result_data["answer"],
                            "time_spent_ms": random.randint(5000, 30000)
                        },
                        "confidence": result_data["confidence"],
                        "result_metadata": {
                            "scenario": scenario.value,
                            "publisher_index": publisher_index,
                            "submission_count": submission,
                            "task_type": task_type,
                            "options_available": result_data["options_available"]
                        }
                    }
                    
                    headers = {"X-API-Key": self.publisher_api_keys[self.publisher_ids.index(publisher_id)]}
                    response = requests.post(f"{TASKS_API_URL}/{task_id}/result", json=submission_data, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        submitted_results.append(result)
                        scenario_results.append(result_data["answer"])
                        print(f"  Session {session_id}: {result_data['answer']} (confidence: {result_data['confidence']:.2f})")
                    elif response.status_code == 429:
                        print(f"  Rate limited for session {session_id}. Waiting 2 seconds...")
                        time.sleep(2)  # Wait 2 seconds on rate limit
                        # Retry once
                        response = requests.post(f"{TASKS_API_URL}/{task_id}/result", json=submission_data, headers=headers)
                        if response.status_code == 200:
                            result = response.json()
                            submitted_results.append(result)
                            scenario_results.append(result_data["answer"])
                            print(f"  Session {session_id} (retry): {result_data['answer']} (confidence: {result_data['confidence']:.2f})")
                        else:
                            print(f"  Failed retry for session {session_id}: {response.status_code} - {response.text}")
                    else:
                        print(f"  Failed to submit result for session {session_id}: {response.status_code} - {response.text}")
                    
                    # Add small delay between submissions to prevent rate limiting
                    time.sleep(0.5)
                
                publisher_index += 1
        
        # Analyze results for this scenario
        self._analyze_scenario_results(scenario, scenario_results, task)
        
        print(f"Submitted {len(submitted_results)} results for task {task_id}")
        return submitted_results

    def _analyze_scenario_results(self, scenario: ConsensusScenario, results: List[str], task: Dict[str, Any]) -> None:
        """Analyze the results for a specific scenario"""
        if not results:
            return
            
        # Count occurrences of each answer
        answer_counts = {}
        for answer in results:
            answer_counts[answer] = answer_counts.get(answer, 0) + 1
        
        total_submissions = len(results)
        most_common_answer = max(answer_counts.items(), key=lambda x: x[1])
        agreement_rate = most_common_answer[1] / total_submissions
        
        print(f"  Scenario Analysis:")
        print(f"    Total submissions: {total_submissions}")
        print(f"    Most common answer: {most_common_answer[0]} ({most_common_answer[1]} times)")
        print(f"    Agreement rate: {agreement_rate:.2%}")
        print(f"    Answer distribution: {dict(answer_counts)}")
        
        # Store for final analysis
        if scenario.value not in self.scenario_results:
            self.scenario_results[scenario.value] = []
        
        self.scenario_results[scenario.value].append({
            "task_id": task["id"],
            "task_type": task.get("task_type"),
            "agreement_rate": agreement_rate,
            "answer_distribution": answer_counts,
            "expected_scenario": scenario.value
        })

    def check_qa_service_status(self, selected_tasks: List[Dict[str, Any]]) -> None:
        """Check QA service status and consensus calculation for tasks"""
        print_step("STEP 6: Check QA service status and consensus calculation")
        
        for task in selected_tasks:
            task_id = task["id"]
            task_type = task.get("task_type", "unknown")
            
            # Check task status through tasks service
            task_response = requests.get(f"{TASKS_API_URL}/{task_id}")
            if task_response.status_code == 200:
                task_data = task_response.json()
                print(f"\nTask {task_id} ({task_type}):")
                print(f"  Status: {task_data.get('status', 'unknown')}")
                print(f"  Assignments: {len(task_data.get('assignments', []))}")
                print(f"  Results: {len(task_data.get('results', []))}")
                print(f"  Consensus Status: {task_data.get('consensus_status', 'unknown')}")
                
                # Check consensus data if available
                consensus_data = task_data.get('consensus_data')
                if consensus_data:
                    print(f"  Consensus Data:")
                    print(f"    Total submissions: {consensus_data.get('total_submissions', 0)}")
                    print(f"    Agreement count: {consensus_data.get('agreement_count', 0)}")
                    print(f"    Agreement score: {consensus_data.get('agreement_score', 0):.3f}")
                    print(f"    Current consensus: {consensus_data.get('current_consensus', {})}")
                else:
                    print(f"  No consensus data available")
            
            # Check QA service directly for validation status
            try:
                # Use the correct endpoint to list all validations
                qa_response = requests.get(f"{QA_SERVICE_URL}/api/v1/validation", headers=INTERNAL_HEADERS)
                if qa_response.status_code == 200:
                    qa_data = qa_response.json()
                    # Filter validations for this task if needed
                    task_validations = [v for v in qa_data if v.get('task_id') == task_id]
                    print(f"  QA Service Validation:")
                    print(f"    Total validations: {len(qa_data)}")
                    print(f"    Task validations: {len(task_validations)}")
                    if task_validations:
                        print(f"    Latest validation status: {task_validations[-1].get('status', 'unknown')}")
                else:
                    print(f"  QA Service Validation: Not found or error ({qa_response.status_code})")
            except Exception as e:
                print(f"  QA Service Validation: Error - {e}")

    def check_consensus_status(self, selected_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check consensus status for all selected tasks"""
        print_step("STEP 8: Check consensus status for all tasks")
        
        consensus_results = {}
        for task in selected_tasks:
            task_id = task["id"]
            response = requests.get(f"{TASKS_API_URL}/{task_id}")
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("status", "unknown")
                
                # Get detailed consensus information
                consensus_data = task_data.get("consensus_data", {})
                agreement_threshold = task_data.get("agreement_threshold", 0.75)
                confidence_threshold = task_data.get("confidence_threshold", 0.6)
                agreement_score = consensus_data.get("agreement_score", 0)
                confidence_scores = consensus_data.get("confidence_scores", [])
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
                
                consensus_results[task_id] = {
                    "status": status,
                    "assignments_count": len(task_data.get("assignments", [])),
                    "results_count": len(task_data.get("results", [])),
                    "consensus_reached": status == "completed",
                    "final_answer": task_data.get("final_answer"),
                    "confidence": task_data.get("confidence"),
                    "agreement_rate": task_data.get("agreement_rate"),
                    "task_type": task.get("task_type"),
                    "scenario": self.task_scenarios.get(task_id, "unknown").value,
                    "consensus_data": consensus_data,
                    "agreement_threshold": agreement_threshold,
                    "confidence_threshold": confidence_threshold,
                    "agreement_score": agreement_score,
                    "avg_confidence": avg_confidence
                }
                
                print(f"Task {task_id} ({task.get('task_type')}): {status}")
                print(f"  Assignments: {consensus_results[task_id]['assignments_count']}, Results: {consensus_results[task_id]['results_count']}")
                print(f"  Agreement Score: {agreement_score:.3f}/{agreement_threshold:.3f}")
                print(f"  Avg Confidence: {avg_confidence:.3f}/{confidence_threshold:.3f}")
                print(f"  Consensus Status: {task_data.get('consensus_status', 'unknown')}")
                
                if consensus_data:
                    print(f"  Consensus Data: {consensus_data}")
                
                # Check if thresholds are met
                if agreement_score >= agreement_threshold and avg_confidence >= confidence_threshold:
                    print(f"  ✅ Thresholds met - should be COMPLETED")
                else:
                    print(f"  ❌ Thresholds not met - agreement: {agreement_score < agreement_threshold}, confidence: {avg_confidence < confidence_threshold}")
            else:
                print(f"Failed to get task {task_id}: {response.status_code}")
        
        return consensus_results

    def generate_comprehensive_report(self, discovery_results: Dict[str, Any], consensus_results: Dict[str, Any]) -> None:
        """Generate a comprehensive report of the testing"""
        print_header("COMPREHENSIVE TESTING REPORT")
        
        print("=== DISCOVERY RESULTS ===")
        print(f"Total tasks in database: {discovery_results['total_tasks']}")
        print(f"Tasks with extractable options: {discovery_results['tasks_with_options']}")
        print(f"Task types discovered: {discovery_results['task_types']}")
        print(f"Categories discovered: {discovery_results['categories']}")
        
        print("\n=== SCENARIO ANALYSIS ===")
        for scenario, results in self.scenario_results.items():
            print(f"\n{scenario.upper()}:")
            avg_agreement = sum(r["agreement_rate"] for r in results) / len(results) if results else 0
            print(f"  Average agreement rate: {avg_agreement:.2%}")
            print(f"  Tasks tested: {len(results)}")
            
            # Show task type distribution
            type_counts = {}
            for result in results:
                task_type = result["task_type"]
                type_counts[task_type] = type_counts.get(task_type, 0) + 1
            print(f"  Task type distribution: {dict(type_counts)}")
        
        print("\n=== CONSENSUS RESULTS ===")
        completed_tasks = sum(1 for result in consensus_results.values() if result.get("consensus_reached"))
        total_tested = len(consensus_results)
        
        if total_tested > 0:
            completion_rate = completed_tasks / total_tested
            print(f"Tasks with consensus reached: {completed_tasks}/{total_tested} ({completion_rate:.1%})")
            
            # Breakdown by task type
            type_results = defaultdict(list)
            for task_id, result in consensus_results.items():
                task_type = result.get("task_type", "unknown")
                type_results[task_type].append(result)
            
            print("\nConsensus by task type:")
            for task_type, results in type_results.items():
                completed = sum(1 for r in results if r.get("consensus_reached"))
                total = len(results)
                if total > 0:
                    rate = completed / total
                    print(f"  {task_type}: {completed}/{total} ({rate:.1%})")
                else:
                    print(f"  {task_type}: 0/0 (0.0%)")
        else:
            print("No tasks were successfully tested due to rate limiting or other issues.")
            print("Please check the API rate limits and try again with fewer concurrent requests.")

def main():
    """Main function to run the dynamic task lifecycle demonstration"""
    print_header("DYNAMIC HOTLABEL TASK LIFECYCLE DEMONSTRATION")
    print("This demo dynamically discovers and tests all available task types and options")
    
    # Initialize the dynamic task lifecycle
    lifecycle = DynamicTaskLifecycle()
    
    try:
        # Step 1: Discover all tasks and their options
        discovery_results = lifecycle.discover_tasks_and_options()
        
        if not lifecycle.tasks:
            print("ERROR: No tasks with extractable options found in database.")
            sys.exit(1)
        
        # Step 2: Select representative tasks for testing
        selected_tasks = lifecycle.select_tasks_for_testing(max_tasks_per_type=3)
        
        # Step 3: Register publishers
        publishers = lifecycle.register_multiple_publishers(count=12)
        if not publishers:
            print("ERROR: Failed to register publishers")
            sys.exit(1)
        
        # Step 4: Create sessions for publishers
        sessions = lifecycle.create_sessions_for_publishers(sessions_per_publisher=2)
        if not sessions:
            print("ERROR: Failed to create sessions")
            sys.exit(1)
        
        # Step 5: Submit results for each selected task
        for task in selected_tasks:
            lifecycle.submit_results_for_task(task, results_per_session=1)
            time.sleep(3)  # Increased delay between tasks to prevent rate limiting
        
        # Wait for QA service to process submissions
        print_step("Waiting for QA service to process submissions...")
        time.sleep(10)  # Wait 10 seconds for QA service to calculate consensus
        
        # Step 6: Manually trigger consensus calculation for each task
        print_step("STEP 6: Manually trigger consensus calculation")
        for task in selected_tasks:
            task_id = task["id"]
            print(f"Triggering consensus calculation for task {task_id}")
            
            # Get task results to trigger consensus
            results_response = requests.get(f"{TASKS_API_URL}/{task_id}/results")
            if results_response.status_code == 200:
                results = results_response.json()
                print(f"  Found {len(results)} results for task {task_id}")
                
                # Trigger consensus calculation by submitting a dummy result
                if results:
                    # Use the last result to trigger consensus
                    last_result = results[-1]
                    trigger_data = {
                        "publisher_id": last_result.get("publisher_id"),
                        "session_id": last_result.get("session_id"),
                        "result": {
                            "label": last_result.get("result", {}).get("label") or last_result.get("result"),
                            "time_spent_ms": random.randint(5000, 30000)
                        },
                        "confidence": last_result.get("confidence", 0.8),
                        "result_metadata": {"trigger": "manual_consensus_calculation"}
                    }
                    
                    trigger_response = requests.post(
                        f"{TASKS_API_URL}/{task_id}/result",
                        json=trigger_data,
                        headers={"X-API-Key": lifecycle.publisher_api_keys[0]}  # Use first publisher's key
                    )
                    if trigger_response.status_code == 200:
                        print(f"  Successfully triggered consensus for task {task_id}")
                    else:
                        print(f"  Failed to trigger consensus for task {task_id}: {trigger_response.status_code}")
                else:
                    print(f"  No results found for task {task_id}")
            else:
                print(f"  Failed to get results for task {task_id}: {results_response.status_code}")
            
            time.sleep(2)  # Small delay between tasks
        
        # Wait a bit more for consensus calculation
        print_step("Waiting for consensus calculation to complete...")
        time.sleep(15)  # Wait 15 seconds for consensus calculation
        
        # Step 7: Check QA service status
        lifecycle.check_qa_service_status(selected_tasks)
        
        # Step 8: Check consensus status
        consensus_results = lifecycle.check_consensus_status(selected_tasks)
        
        # Step 9: Generate comprehensive report
        lifecycle.generate_comprehensive_report(discovery_results, consensus_results)
        
        print("\nDemonstration completed successfully!")
        print("This comprehensive test covered:")
        print(f"  - {len(discovery_results['task_types'])} different task types")
        print(f"  - {len(discovery_results['categories'])} different categories")
        print(f"  - {len(ConsensusScenario)} different consensus scenarios")
        print(f"  - {len(selected_tasks)} representative tasks")
        print(f"  - {len(publishers)} publishers with {sum(len(s) for s in sessions.values())} sessions")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 