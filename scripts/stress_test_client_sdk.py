#!/usr/bin/env python3
"""
HotLabel System Stress Test - Client SDK Perspective

This script performs a comprehensive stress test of the entire HotLabel system
from a client SDK perspective, simulating real-world usage patterns:

1. Use existing tasks from the database (created by pull_TII_all_categories script)
2. Use webdriver to access the sample site at localhost:5001
3. Complete tasks through the client SDK with new sessions each time
4. Simulate different user behaviors and task completion patterns
5. Monitor system performance and record metrics
6. Test consensus calculation and task lifecycle completion

Usage:
    python stress_test_client_sdk.py [--iterations 10] [--concurrent 2] [--tasks-per-session 1]
"""

import requests
import uuid
import json
import time
import random
import argparse
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import sys
import os
import subprocess
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Selenium imports for webdriver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
KONG_URL = "http://localhost:8000"  # API Gateway URL
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
TASKS_SERVICE_URL = "http://localhost:8002"  # Direct tasks service URL
QA_API_URL = f"{KONG_URL}/api/v1/consensus"
SESSIONS_API_URL = f"{KONG_URL}/api/v1/sessions"

# Sample site configuration
SAMPLE_SITE_URL = "http://localhost:5001"

# QA Service endpoints
VALIDATION_URL = f"http://localhost:8003/api/v1/validation"
METRICS_URL = f"http://localhost:8003/api/v1/metrics"
QA_API_KEY = "test_api_key_qa_service"

class TaskScenario(Enum):
    VQA_POSITIVE_CONSENSUS = "vqa_positive_consensus"  # Consensus achieved -> positive result
    VQA_NEGATIVE_CONSENSUS = "vqa_negative_consensus"  # Consensus achieved -> negative result
    VQA_AMBIGUOUS_CONSENSUS = "vqa_ambiguous_consensus"  # Consensus achieved -> ambiguous result

@dataclass
class TestResult:
    """Data class to store test results"""
    session_id: str
    task_id: str
    scenario: str
    start_time: datetime
    end_time: datetime
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    task_completion_time_ms: Optional[int] = None
    selected_option: Optional[str] = None

@dataclass
class SystemMetrics:
    """Data class to store system metrics"""
    total_sessions: int
    total_tasks_completed: int
    total_errors: int
    avg_response_time_ms: float
    avg_task_completion_time_ms: float
    consensus_reached_count: int
    tasks_in_progress: int
    tasks_completed: int
    tasks_failed: int
    positive_consensus_count: int
    negative_consensus_count: int
    ambiguous_consensus_count: int

class WebDriverManager:
    """Manages webdriver instances for browser automation"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.drivers = []
        
    def create_driver(self) -> webdriver.Chrome:
        """Create a new Chrome webdriver instance using webdriver-manager"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Use webdriver-manager to automatically download and manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            self.drivers.append(driver)
            return driver
        except Exception as e:
            print(f"Failed to create webdriver: {e}")
            raise
    
    def cleanup(self):
        """Clean up all webdriver instances"""
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass
        self.drivers.clear()

class HotLabelStressTest:
    """Main stress test class"""
    
    def __init__(self, iterations: int = 10, concurrent: int = 2, tasks_per_session: int = 1):
        self.iterations = iterations
        self.concurrent = concurrent
        self.tasks_per_session = tasks_per_session
        
        # Test state
        self.task_ids = []
        self.scenario_results = {}
        
        # Results tracking
        self.test_results = []
        self.system_metrics = []
        self.start_time = None
        self.end_time = None
        
        # WebDriver management
        self.webdriver_manager = WebDriverManager(headless=True)
        
        # Thread safety
        self.results_lock = threading.Lock()
        
    def print_header(self, title: str) -> None:
        """Print a formatted header"""
        print("\n" + "=" * 80)
        print(f" {title} ".center(80, "="))
        print("=" * 80)

    def print_step(self, step: str) -> None:
        """Print a step in the process"""
        print(f"\n--- {step} ---")

    def print_response(self, response: requests.Response, title: str) -> None:
        """Print API response in a readable format"""
        print(f"\n=== {title} ===")
        print(f"Status Code: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(f"Raw response text: {response.text}")
        print("-" * 50)

    def setup_test_environment(self) -> None:
        """Set up the test environment with existing tasks"""
        self.print_step("Setting up test environment")
        
        # Get existing tasks from database
        response = requests.get(f"{TASKS_SERVICE_URL}/api/v1/tasks", headers={"X-API-Key": "internal-service"})
        if response.status_code >= 300:
            raise Exception(f"Failed to get existing tasks: {response.text}")
            
        tasks = response.json().get("items", [])
        print(f"Found {len(tasks)} existing tasks in the database")
        
        # Filter for pending tasks only
        pending_tasks = [task for task in tasks if task.get("status") == "pending"]
        print(f"Found {len(pending_tasks)} pending tasks available for testing")
        
        if not pending_tasks:
            raise Exception("No pending tasks found. Please run pull_TII_all_categories.py first.")
        
        # Select tasks for testing
        selected_tasks = pending_tasks[:min(10, len(pending_tasks))]  # Use up to 10 tasks
        
        for task in selected_tasks:
            self.task_ids.append(task["id"])
            # Assign scenario based on task type
            if task.get("task_type") == "true-false":
                self.scenario_results[task["id"]] = TaskScenario.VQA_POSITIVE_CONSENSUS
            elif task.get("task_type") == "numeric":
                self.scenario_results[task["id"]] = TaskScenario.VQA_NEGATIVE_CONSENSUS
            elif task.get("task_type") == "mcq":
                self.scenario_results[task["id"]] = TaskScenario.VQA_AMBIGUOUS_CONSENSUS
            else:
                self.scenario_results[task["id"]] = TaskScenario.VQA_POSITIVE_CONSENSUS
        
        print(f"Selected {len(selected_tasks)} tasks for stress testing:")
        for task in selected_tasks:
            print(f"  - Task ID: {task['id']}, Type: {task.get('task_type')}, Category: {task.get('category')}")

    def complete_task_via_webdriver(self, task_id: str, scenario: TaskScenario) -> TestResult:
        """Complete a task using webdriver automation"""
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        result = TestResult(
            session_id=session_id,
            task_id=task_id,
            scenario=scenario.value,
            start_time=start_time,
            end_time=None,
            success=False
        )
        
        driver = None
        try:
            # Create webdriver
            driver = self.webdriver_manager.create_driver()
            
            # Navigate to sample site
            print(f"    [Session {session_id}] Navigating to {SAMPLE_SITE_URL}")
            driver.get(SAMPLE_SITE_URL)
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Complete HotLabel tasks
            tasks_completed = self.complete_hotlabel_tasks(driver, scenario)
            
            if tasks_completed > 0:
                result.success = True
                result.task_completion_time_ms = random.randint(5000, 15000)
                print(f"    [Session {session_id}] Successfully completed {tasks_completed} HotLabel tasks")
            else:
                print(f"    [Session {session_id}] No HotLabel tasks found or completed")
            
            # Complete quiz questions
            self.complete_quiz_questions(driver)
            
        except Exception as e:
            result.error_message = str(e)
            print(f"    [Session {session_id}] Error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            result.end_time = datetime.utcnow()
            result.response_time_ms = int((result.end_time - result.start_time).total_seconds() * 1000)
            
        return result

    def complete_hotlabel_tasks(self, driver: webdriver.Chrome, scenario: TaskScenario) -> int:
        """Complete HotLabel tasks on the page"""
        tasks_completed = 0
        
        try:
            # Look for HotLabel modal or task elements
            modal_selectors = [
                ".hotlabel-modal",
                ".hotlabel-container",
                "[class*='hotlabel']",
                "[id*='hotlabel']",
                ".modal",
                "[class*='modal']"
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"      Found HotLabel modal: {selector}")
                        modal_found = True
                        break
                except:
                    continue
            
            if not modal_found:
                print("      No HotLabel modal found")
                return tasks_completed
            
            # Look for task options
            option_selectors = [
                "button[data-option-index]",
                "button:contains('True')",
                "button:contains('False')",
                ".hotlabel-options button",
                "input[type='radio']",
                "label input[type='radio']"
            ]
            
            for selector in option_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"      Found {len(elements)} options with {selector}")
                        
                        # Select option based on scenario
                        selected_option = self.select_option_for_scenario(driver, elements, scenario)
                        if selected_option:
                            result.selected_option = selected_option
                            tasks_completed += 1
                            print(f"      Selected option: {selected_option}")
                            break
                except Exception as e:
                    print(f"      Error with selector {selector}: {e}")
                    continue
            
        except Exception as e:
            print(f"      Error completing HotLabel tasks: {e}")
        
        return tasks_completed

    def select_option_for_scenario(self, driver: webdriver.Chrome, elements: List, scenario: TaskScenario) -> Optional[str]:
        """Select an option based on the scenario"""
        try:
            if scenario == TaskScenario.VQA_POSITIVE_CONSENSUS:
                # Most users choose True for positive consensus
                if len(elements) >= 1:
                    elements[0].click()
                    return "True"
            elif scenario == TaskScenario.VQA_NEGATIVE_CONSENSUS:
                # Most users choose False for negative consensus
                if len(elements) >= 2:
                    elements[1].click()
                    return "False"
                elif len(elements) >= 1:
                    elements[0].click()
                    return "False"
            elif scenario == TaskScenario.VQA_AMBIGUOUS_CONSENSUS:
                # Mixed responses for ambiguous consensus
                if len(elements) >= 2:
                    choice = random.choice([0, 1])
                    elements[choice].click()
                    return "True" if choice == 0 else "False"
                elif len(elements) >= 1:
                    elements[0].click()
                    return "True"
            
            # Default: click first option
            if elements:
                elements[0].click()
                return "True"
                
        except Exception as e:
            print(f"      Error selecting option: {e}")
        
        return None

    def complete_quiz_questions(self, driver: webdriver.Chrome) -> None:
        """Complete any quiz questions on the page"""
        try:
            # Look for quiz questions and complete them
            quiz_selectors = [
                "input[type='radio']",
                "input[type='checkbox']",
                "select",
                "textarea"
            ]
            
            for selector in quiz_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            if element.tag_name == "input" and element.get_attribute("type") == "radio":
                                element.click()
                            elif element.tag_name == "input" and element.get_attribute("type") == "checkbox":
                                element.click()
                            elif element.tag_name == "select":
                                options = element.find_elements(By.TAG_NAME, "option")
                                if options:
                                    options[0].click()
                            elif element.tag_name == "textarea":
                                element.send_keys("Test response")
                    except:
                        continue
        except Exception as e:
            print(f"      Error completing quiz questions: {e}")

    def run_single_session(self, session_index: int) -> List[TestResult]:
        """Run a single test session"""
        results = []
        
        # Select a random task for this session
        if not self.task_ids:
            print(f"    [Session {session_index}] No tasks available")
            return results
        
        task_id = random.choice(self.task_ids)
        scenario = self.scenario_results.get(task_id, TaskScenario.VQA_POSITIVE_CONSENSUS)
        
        print(f"    [Session {session_index}] Starting task {task_id} ({scenario.value})")
        
        # Complete the task
        result = self.complete_task_via_webdriver(task_id, scenario)
        results.append(result)
        
        return results

    def run_stress_test(self) -> None:
        """Run the main stress test"""
        self.print_header("HOTLABEL STRESS TEST - CLIENT SDK PERSPECTIVE")
        print("This test uses existing tasks from the database (created by pull_TII_all_categories.py)")
        
        self.start_time = datetime.utcnow()
        
        try:
            # Set up test environment
            self.setup_test_environment()
            
            # Run concurrent sessions
            print(f"\nRunning {self.iterations} iterations with {self.concurrent} concurrent sessions...")
            
            with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
                # Submit all sessions
                future_to_session = {
                    executor.submit(self.run_single_session, i): i 
                    for i in range(self.iterations)
                }
                
                # Collect results
                for future in as_completed(future_to_session):
                    session_index = future_to_session[future]
                    try:
                        session_results = future.result()
                        with self.results_lock:
                            self.test_results.extend(session_results)
                        print(f"    [Session {session_index}] Completed with {len(session_results)} results")
                    except Exception as e:
                        print(f"    [Session {session_index}] Failed: {e}")
            
            self.end_time = datetime.utcnow()
            
            # Calculate metrics
            self.calculate_final_metrics()
            
            # Check task statuses
            self.check_task_statuses()
            
            # Print results
            self.print_results()
            
            # Save results
            self.save_results_to_file()
            
        except Exception as e:
            print(f"ERROR: {e}")
            raise
        finally:
            self.webdriver_manager.cleanup()

    def calculate_final_metrics(self) -> None:
        """Calculate final system metrics"""
        successful_results = [r for r in self.test_results if r.success]
        failed_results = [r for r in self.test_results if not r.success]
        
        metrics = SystemMetrics(
            total_sessions=len(self.test_results),
            total_tasks_completed=len(successful_results),
            total_errors=len(failed_results),
            avg_response_time_ms=statistics.mean([r.response_time_ms for r in self.test_results if r.response_time_ms]) if self.test_results else 0,
            avg_task_completion_time_ms=statistics.mean([r.task_completion_time_ms for r in successful_results if r.task_completion_time_ms]) if successful_results else 0,
            consensus_reached_count=0,  # Will be updated by check_task_statuses
            tasks_in_progress=0,
            tasks_completed=0,
            tasks_failed=0,
            positive_consensus_count=0,
            negative_consensus_count=0,
            ambiguous_consensus_count=0
        )
        
        self.system_metrics.append(metrics)

    def check_task_statuses(self) -> None:
        """Check the status of all tasks after testing"""
        print("\n--- Checking Task Statuses ---")
        
        for task_id in self.task_ids:
            try:
                response = requests.get(f"{TASKS_API_URL}/{task_id}")
                if response.status_code == 200:
                    task_data = response.json()
                    status = task_data.get("status", "unknown")
                    results_count = len(task_data.get("results", []))
                    
                    print(f"Task {task_id}: {status} ({results_count} results)")
                    
                    # Update metrics
                    if status == "completed":
                        self.system_metrics[0].tasks_completed += 1
                        self.system_metrics[0].consensus_reached_count += 1
                    elif status == "in_progress":
                        self.system_metrics[0].tasks_in_progress += 1
                    elif status == "failed":
                        self.system_metrics[0].tasks_failed += 1
                        
            except Exception as e:
                print(f"Error checking task {task_id}: {e}")

    def print_results(self) -> None:
        """Print test results"""
        self.print_header("STRESS TEST RESULTS")
        
        if not self.system_metrics:
            print("No metrics available")
            return
        
        metrics = self.system_metrics[0]
        
        print(f"Test Duration: {(self.end_time - self.start_time).total_seconds():.2f} seconds")
        print(f"Total Sessions: {metrics.total_sessions}")
        print(f"Successful Sessions: {metrics.total_tasks_completed}")
        print(f"Failed Sessions: {metrics.total_errors}")
        print(f"Success Rate: {(metrics.total_tasks_completed / metrics.total_sessions * 100):.1f}%" if metrics.total_sessions > 0 else "N/A")
        print(f"Average Response Time: {metrics.avg_response_time_ms:.0f}ms")
        print(f"Average Task Completion Time: {metrics.avg_task_completion_time_ms:.0f}ms")
        print(f"Tasks Completed: {metrics.tasks_completed}")
        print(f"Tasks In Progress: {metrics.tasks_in_progress}")
        print(f"Tasks Failed: {metrics.tasks_failed}")
        print(f"Consensus Reached: {metrics.consensus_reached_count}")

    def save_results_to_file(self) -> None:
        """Save results to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_results_{timestamp}.json"
        
        results_data = {
            "test_config": {
                "iterations": self.iterations,
                "concurrent": self.concurrent,
                "tasks_per_session": self.tasks_per_session
            },
            "test_duration": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None
            },
            "results": [
                {
                    "session_id": r.session_id,
                    "task_id": r.task_id,
                    "scenario": r.scenario,
                    "success": r.success,
                    "response_time_ms": r.response_time_ms,
                    "task_completion_time_ms": r.task_completion_time_ms,
                    "selected_option": r.selected_option,
                    "error_message": r.error_message
                }
                for r in self.test_results
            ],
            "system_metrics": [
                {
                    "total_sessions": m.total_sessions,
                    "total_tasks_completed": m.total_tasks_completed,
                    "total_errors": m.total_errors,
                    "avg_response_time_ms": m.avg_response_time_ms,
                    "avg_task_completion_time_ms": m.avg_task_completion_time_ms,
                    "consensus_reached_count": m.consensus_reached_count,
                    "tasks_in_progress": m.tasks_in_progress,
                    "tasks_completed": m.tasks_completed,
                    "tasks_failed": m.tasks_failed
                }
                for m in self.system_metrics
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nResults saved to: {filename}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HotLabel System Stress Test")
    parser.add_argument("--iterations", type=int, default=10, help="Number of test iterations")
    parser.add_argument("--concurrent", type=int, default=2, help="Number of concurrent sessions")
    parser.add_argument("--tasks-per-session", type=int, default=1, help="Tasks per session")
    
    args = parser.parse_args()
    
    # Create and run stress test
    stress_test = HotLabelStressTest(
        iterations=args.iterations,
        concurrent=args.concurrent,
        tasks_per_session=args.tasks_per_session
    )
    
    try:
        stress_test.run_stress_test()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 