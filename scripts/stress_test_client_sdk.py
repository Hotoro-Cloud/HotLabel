#!/usr/bin/env python3
"""
HotLabel System Stress Test - Client SDK Perspective

This script performs a comprehensive stress test of the entire HotLabel system
from a client SDK perspective, simulating real-world usage patterns:

1. Register a single provider at the beginning
2. Create multiple VQA tasks with different consensus scenarios
3. Use webdriver to access the sample site at localhost:5001
4. Complete tasks through the client SDK with new sessions each time
5. Simulate different user behaviors and task completion patterns
6. Monitor system performance and record metrics
7. Test consensus calculation and task lifecycle completion

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
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
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
        self.provider_id = None
        self.provider_api_key = None
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
        """Set up the test environment with provider and tasks"""
        self.print_step("Setting up test environment")
        
        # Register provider
        provider_data = {
            "name": "Stress Test Provider",
            "contact_email": f"stress_test_provider_{uuid.uuid4().hex[:8]}@example.com",
            "description": "Provider for stress testing the HotLabel system",
            "website": "https://example.com/stress-test-provider"
        }
        
        response = requests.post(PROVIDERS_API_URL, json=provider_data)
        if response.status_code >= 300:
            raise Exception(f"Failed to register provider: {response.text}")
            
        result = response.json()
        self.provider_id = result["id"]
        self.provider_api_key = result["api_key"]
        print(f"Provider registered: {self.provider_id}")
        
        # Create tasks for different scenarios
        self.create_test_tasks()
        
    def create_test_tasks(self) -> None:
        """Create test tasks for different consensus scenarios"""
        self.print_step("Creating test tasks for consensus scenarios")
        
        scenarios = [
            TaskScenario.VQA_POSITIVE_CONSENSUS,
            TaskScenario.VQA_NEGATIVE_CONSENSUS,
            TaskScenario.VQA_AMBIGUOUS_CONSENSUS
        ]
        
        for scenario in scenarios:
            task_data = self.create_task_data_for_scenario(scenario)
            
            headers = {"X-API-Key": self.provider_api_key}
            response = requests.post(TASKS_API_URL, json=task_data, headers=headers)
            
            if response.status_code >= 300:
                print(f"Failed to create task for {scenario.value}: {response.text}")
                continue
                
            result = response.json()
            task_id = str(result["id"])
            self.task_ids.append(task_id)
            self.scenario_results[task_id] = scenario
            
            print(f"Created task {task_id} for scenario {scenario.value}")
    
    def create_task_data_for_scenario(self, scenario: TaskScenario) -> Dict[str, Any]:
        """Create task data for a specific consensus scenario"""
        base_data = {
            "title": f"Stress Test - {scenario.value}",
            "description": f"Stress test task for {scenario.value} scenario",
            "provider_id": self.provider_id,
            "task_type": "true-false",
            "category": "vqa",
            "complexity_level": 1,
            "topic": scenario.value.replace("vqa_", "").replace("_consensus", ""),
            "agreement_threshold": 0.7,
            "confidence_threshold": 0.6,
            "status": "pending",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }
        
        if scenario == TaskScenario.VQA_POSITIVE_CONSENSUS:
            base_data.update({
                "content": {
                    "image_url": "https://s3-eu-north-1-derc-wmi-crowdlabel-production.s3.eu-north-1.amazonaws.com/tii_vqa_0whejvjm9blfgjb6.png",
                    "image_filename": "tii_vqa_0whejvjm9blfgjb6.png",
                    "question": "Is there anything else that is the same shape as the tiny blue rubber thing?"
                },
                "task": {
                    "text": "Is there anything else that is the same shape as the tiny blue rubber thing?",
                    "choices": [
                        {"key": "a", "value": "True"},
                        {"key": "b", "value": "False"}
                    ]
                },
                "track_id": "t-stress-test-positive-consensus"
            })
        elif scenario == TaskScenario.VQA_NEGATIVE_CONSENSUS:
            base_data.update({
                "content": {
                    "image_url": "https://s3-eu-north-1-derc-wmi-crowdlabel-production.s3.eu-north-1.amazonaws.com/tii_vqa_whbf6cf3umuoijcl.png",
                    "image_filename": "tii_vqa_whbf6cf3umuoijcl.png",
                    "question": "Is there a tiny red object made of the same material as the large gray bag?"
                },
                "task": {
                    "text": "Is there a tiny red object made of the same material as the large gray bag?",
                    "choices": [
                        {"key": "a", "value": "True"},
                        {"key": "b", "value": "False"}
                    ]
                },
                "track_id": "t-stress-test-negative-consensus"
            })
        elif scenario == TaskScenario.VQA_AMBIGUOUS_CONSENSUS:
            base_data.update({
                "content": {
                    "image_url": "https://s3-eu-north-1-derc-wmi-crowdlabel-production.s3.eu-north-1.amazonaws.com/tii_vqa_ambiguous.png",
                    "image_filename": "tii_vqa_ambiguous.png",
                    "question": "Is there a green object that is both soft and metallic?"
                },
                "task": {
                    "text": "Is there a green object that is both soft and metallic?",
                    "choices": [
                        {"key": "a", "value": "True"},
                        {"key": "b", "value": "False"}
                    ]
                },
                "track_id": "t-stress-test-ambiguous-consensus"
            })
        
        return base_data
    
    def complete_task_via_webdriver(self, task_id: str, scenario: TaskScenario) -> TestResult:
        """Complete a task using webdriver to simulate real user interaction"""
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
            print(f"    Starting task completion for task {task_id} ({scenario.value})")
            
            # Create new webdriver instance for this session
            driver = self.webdriver_manager.create_driver()
            
            # Navigate to sample site
            print(f"    Navigating to {SAMPLE_SITE_URL}")
            driver.get(SAMPLE_SITE_URL)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for the page to fully load and any initial content to appear
            time.sleep(3)  # Increased wait time for HotLabel modal to appear
            
            # Debug: Print page title and URL
            print(f"    Page title: {driver.title}")
            print(f"    Current URL: {driver.current_url}")
            
            # Check for HotLabel modal and complete tasks if present
            hotlabel_tasks_completed = self.complete_hotlabel_tasks(driver, scenario)
            print(f"    Completed {hotlabel_tasks_completed} HotLabel tasks")
            
            # Look for the Start Quiz button - it's a form submit button, not a link
            try:
                print("    Looking for Start Quiz button...")
                # First try to find the Start Quiz button
                start_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start Quiz')]"))
                )
                print("    Found Start Quiz button, clicking...")
                start_button.click()
            except TimeoutException:
                print("    Start Quiz button not found, trying alternative methods...")
                # If Start Quiz button not found, try to find any button that might start the quiz
                try:
                    start_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                    )
                    print("    Found submit button, clicking...")
                    start_button.click()
                except TimeoutException:
                    print("    No buttons found, navigating directly to quiz page...")
                    # If still not found, try to navigate directly to quiz page
                    driver.get(f"{SAMPLE_SITE_URL}/quiz")
            
            # Wait for quiz page to load
            print("    Waiting for quiz page to load...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            print(f"    Quiz page loaded: {driver.current_url}")
            
            # Complete the quiz (simulate user answering questions)
            print("    Completing quiz questions...")
            self.complete_quiz_questions(driver)
            
            # Submit the quiz
            print("    Submitting quiz...")
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Wait for result page
            print("    Waiting for result page...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print(f"    Result page loaded: {driver.current_url}")
            
            # Check for HotLabel modal again on result page
            hotlabel_tasks_completed += self.complete_hotlabel_tasks(driver, scenario)
            print(f"    Total HotLabel tasks completed: {hotlabel_tasks_completed}")
            
            # Record successful completion
            end_time = datetime.utcnow()
            result.end_time = end_time
            result.success = True
            result.response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            print(f"    Successfully completed task {task_id} via webdriver")
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            result.end_time = end_time
            result.success = False
            result.error_message = str(e)
            result.response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            print(f"    Failed to complete task {task_id}: {e}")
            
            # Debug: Print page source if there's an error
            if driver:
                try:
                    print(f"      Current URL: {driver.current_url}")
                    print(f"      Page title: {driver.title}")
                    # Print first 500 characters of page source for debugging
                    page_source = driver.page_source[:500]
                    print(f"      Page source (first 500 chars): {page_source}")
                except:
                    pass
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def complete_hotlabel_tasks(self, driver: webdriver.Chrome, scenario: TaskScenario) -> int:
        """Complete HotLabel tasks if modal is present"""
        tasks_completed = 0
        
        try:
            # Wait a bit for any modals to appear
            time.sleep(2)
            
            # Look for HotLabel modal - check multiple possible selectors
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
                    modal = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"      Found HotLabel modal with selector: {selector}")
                    modal_found = True
                    break
                except TimeoutException:
                    continue
            
            if not modal_found:
                print("      No HotLabel modal found")
                return tasks_completed
            
            # Complete VQA task based on scenario
            vqa_completed = self.complete_vqa_task(driver, scenario)
            if vqa_completed:
                tasks_completed += 1
                print("      Completed VQA task")
            
            print(f"      Completed {tasks_completed} HotLabel tasks")
            
        except Exception as e:
            print(f"      Error completing HotLabel tasks: {e}")
        
        return tasks_completed
    
    def complete_vqa_task(self, driver: webdriver.Chrome, scenario: TaskScenario) -> bool:
        """Complete a VQA (Visual Question Answering) task based on scenario"""
        try:
            # Look for VQA-specific elements based on the HotLabel SDK structure
            # The modal should have: question, image, and True/False option buttons
            
            # Check for image (VQA tasks always have an image)
            images = driver.find_elements(By.CSS_SELECTOR, "img")
            if not images:
                print("        No images found for VQA task")
                return False
            
            print(f"        Found {len(images)} images for VQA task")
            
            # Look for True/False option buttons based on HotLabel SDK structure
            # The SDK creates buttons with data-option-index attributes
            option_selectors = [
                ".hotlabel-options button[data-option-index]",
                ".hotlabel-options button",
                "button[data-option-index]",
                "button:contains('True')",
                "button:contains('False')",
                "input[value='True']",
                "input[value='False']",
                "label:contains('True')",
                "label:contains('False')"
            ]
            
            selected_option = None
            for selector in option_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"        Found {len(elements)} option elements with selector: {selector}")
                        
                        # Select option based on scenario to achieve desired consensus
                        selected_option = self.select_option_for_scenario(driver, elements, scenario)
                        if selected_option:
                            print(f"        Selected VQA option: {selected_option}")
                            # The result is submitted immediately when option is clicked
                            print("        Task result submitted automatically")
                            return True
                        break
                except Exception as e:
                    print(f"        Error with selector {selector}: {e}")
                    continue
            
            if not selected_option:
                print("        No options found or selected")
                return False
            
            return True
            
        except Exception as e:
            print(f"        Error completing VQA task: {e}")
            return False
    
    def select_option_for_scenario(self, driver: webdriver.Chrome, elements: List, scenario: TaskScenario) -> Optional[str]:
        """Select an option based on the consensus scenario to achieve desired results"""
        try:
            if not elements:
                return None
            
            # Get the text/value of each option
            options = []
            for element in elements:
                try:
                    # Try different ways to get the option text/value
                    option_text = element.text.strip()
                    option_value = element.get_attribute('value')
                    option_data = element.get_attribute('data-option-index')
                    
                    if option_text:
                        options.append(option_text)
                    elif option_value:
                        options.append(option_value)
                    elif option_data is not None:
                        # If we have data-option-index, use the index to determine True/False
                        index = int(option_data)
                        options.append("True" if index == 0 else "False")
                except:
                    continue
            
            print(f"          Available options: {options}")
            
            if not options:
                return None
            
            # Select option based on scenario to achieve desired consensus
            if scenario == TaskScenario.VQA_POSITIVE_CONSENSUS:
                # For positive consensus, prefer "True" answers
                if "True" in options:
                    selected_text = "True"
                else:
                    selected_text = random.choice(options)
            elif scenario == TaskScenario.VQA_NEGATIVE_CONSENSUS:
                # For negative consensus, prefer "False" answers
                if "False" in options:
                    selected_text = "False"
                else:
                    selected_text = random.choice(options)
            elif scenario == TaskScenario.VQA_AMBIGUOUS_CONSENSUS:
                # For ambiguous consensus, random selection to create split
                selected_text = random.choice(options)
            else:
                # Default random selection
                selected_text = random.choice(options)
            
            # Find and click the element with the selected option
            for element in elements:
                try:
                    element_text = element.text.strip()
                    element_value = element.get_attribute('value')
                    element_data = element.get_attribute('data-option-index')
                    
                    if (element_text == selected_text or 
                        element_value == selected_text or
                        (element_data is not None and 
                         ((int(element_data) == 0 and selected_text == "True") or
                          (int(element_data) == 1 and selected_text == "False")))):
                        
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(2)  # Wait for automatic submission to complete
                        return selected_text
                except:
                    continue
            
            # Fallback: click the first element
            if elements:
                driver.execute_script("arguments[0].click();", elements[0])
                time.sleep(2)  # Wait for automatic submission to complete
                return options[0] if options else "Unknown"
            
            return None
            
        except Exception as e:
            print(f"          Error selecting option: {e}")
            return None
    
    def complete_quiz_questions(self, driver: webdriver.Chrome) -> None:
        """Complete quiz questions by selecting random answers"""
        # Find all radio buttons
        radio_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        
        # Group radio buttons by question
        questions = {}
        for radio in radio_buttons:
            name = radio.get_attribute("name")
            if name not in questions:
                questions[name] = []
            questions[name].append(radio)
        
        # Select one answer per question
        for question_name, radios in questions.items():
            if radios:
                # Select a random answer
                selected_radio = random.choice(radios)
                driver.execute_script("arguments[0].click();", selected_radio)
                time.sleep(0.5)  # Small delay to simulate human interaction
    
    def run_single_session(self, session_index: int) -> List[TestResult]:
        """Run a single session with multiple task completions"""
        session_results = []
        
        # Select random tasks for this session
        selected_tasks = random.sample(self.task_ids, min(self.tasks_per_session, len(self.task_ids)))
        
        for task_index, task_id in enumerate(selected_tasks):
            scenario = self.scenario_results[task_id]
            
            print(f"Session {session_index + 1}, Task {task_index + 1}: Completing {scenario.value}")
            
            # Complete task via webdriver
            result = self.complete_task_via_webdriver(task_id, scenario)
            session_results.append(result)
            
            # Small delay between tasks
            time.sleep(random.uniform(1, 3))
        
        return session_results
    
    def run_stress_test(self) -> None:
        """Run the main stress test"""
        self.print_header("Starting HotLabel System Stress Test")
        self.start_time = datetime.utcnow()
        
        try:
            # Set up test environment
            self.setup_test_environment()
            
            print(f"Created {len(self.task_ids)} tasks for testing")
            print(f"Task IDs: {self.task_ids}")
            
            # Run stress test with concurrent sessions
            with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
                # Submit all sessions
                future_to_session = {
                    executor.submit(self.run_single_session, i): i 
                    for i in range(self.iterations)
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_session):
                    session_index = future_to_session[future]
                    try:
                        session_results = future.result()
                        with self.results_lock:
                            self.test_results.extend(session_results)
                        print(f"Completed session {session_index + 1} with {len(session_results)} results")
                    except Exception as e:
                        print(f"Session {session_index + 1} failed: {e}")
                        # Add a failed result to track the error
                        failed_result = TestResult(
                            session_id=str(uuid.uuid4()),
                            task_id="unknown",
                            scenario="failed_session",
                            start_time=datetime.utcnow(),
                            end_time=datetime.utcnow(),
                            success=False,
                            error_message=str(e)
                        )
                        with self.results_lock:
                            self.test_results.append(failed_result)
            
            print(f"Total results collected: {len(self.test_results)}")
            successful_count = len([r for r in self.test_results if r.success])
            failed_count = len([r for r in self.test_results if not r.success])
            print(f"Successful: {successful_count}, Failed: {failed_count}")
            
            # Calculate final metrics
            self.calculate_final_metrics()
            
        except Exception as e:
            print(f"Stress test failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.end_time = datetime.utcnow()
            self.webdriver_manager.cleanup()
    
    def calculate_final_metrics(self) -> None:
        """Calculate final system metrics"""
        self.print_step("Calculating final metrics")
        
        successful_results = [r for r in self.test_results if r.success]
        failed_results = [r for r in self.test_results if not r.success]
        
        # Calculate response times only if there are successful results
        response_times = [r.response_time_ms for r in successful_results if r.response_time_ms]
        task_completion_times = [r.task_completion_time_ms for r in successful_results if r.task_completion_time_ms]
        
        # Calculate averages with proper error handling
        avg_response_time_ms = statistics.mean(response_times) if response_times else 0
        avg_task_completion_time_ms = statistics.mean(task_completion_times) if task_completion_times else 0
        
        metrics = SystemMetrics(
            total_sessions=self.iterations,
            total_tasks_completed=len(successful_results),
            total_errors=len(failed_results),
            avg_response_time_ms=avg_response_time_ms,
            avg_task_completion_time_ms=avg_task_completion_time_ms,
            consensus_reached_count=0,  # Will be calculated separately
            tasks_in_progress=0,
            tasks_completed=0,
            tasks_failed=0,
            positive_consensus_count=0,
            negative_consensus_count=0,
            ambiguous_consensus_count=0
        )
        
        self.system_metrics.append(metrics)
        
        # Check task statuses and consensus results
        self.check_task_statuses()
    
    def check_task_statuses(self) -> None:
        """Check the status of all created tasks and consensus results"""
        self.print_step("Checking task statuses and consensus results")
        
        # Wait a bit for consensus calculation to complete
        print("Waiting 10 seconds for consensus calculation...")
        time.sleep(10)
        
        headers = {"X-API-Key": self.provider_api_key}
        
        for task_id in self.task_ids:
            try:
                response = requests.get(f"{TASKS_API_URL}/{task_id}", headers=headers)
                if response.status_code == 200:
                    task_data = response.json()
                    status = task_data.get("status", "unknown")
                    scenario = self.scenario_results[task_id]
                    
                    print(f"\nTask {task_id} ({scenario.value}):")
                    print(f"  Status: {status}")
                    
                    # Update metrics
                    if status == "completed":
                        self.system_metrics[0].tasks_completed += 1
                    elif status == "in_progress":
                        self.system_metrics[0].tasks_in_progress += 1
                    elif status == "failed":
                        self.system_metrics[0].tasks_failed += 1
                    
                    # Check consensus data
                    consensus_data = task_data.get("consensus_data", {})
                    if consensus_data:
                        current_consensus = consensus_data.get("current_consensus")
                        total_submissions = consensus_data.get("total_submissions", 0)
                        agreement_count = consensus_data.get("agreement_count", 0)
                        
                        print(f"  Total Submissions: {total_submissions}")
                        print(f"  Agreement Count: {agreement_count}")
                        print(f"  Current Consensus: {current_consensus}")
                        
                        if current_consensus:
                            self.system_metrics[0].consensus_reached_count += 1
                            
                            # Categorize consensus by scenario
                            if scenario == TaskScenario.VQA_POSITIVE_CONSENSUS:
                                self.system_metrics[0].positive_consensus_count += 1
                            elif scenario == TaskScenario.VQA_NEGATIVE_CONSENSUS:
                                self.system_metrics[0].negative_consensus_count += 1
                            elif scenario == TaskScenario.VQA_AMBIGUOUS_CONSENSUS:
                                self.system_metrics[0].ambiguous_consensus_count += 1
                    else:
                        print(f"  No consensus data available")
                        
                    # Also check for results
                    try:
                        results_response = requests.get(f"{TASKS_API_URL}/{task_id}/results", headers=headers)
                        if results_response.status_code == 200:
                            results = results_response.json()
                            print(f"  Total Results: {len(results)}")
                            for i, result in enumerate(results[:3]):  # Show first 3 results
                                print(f"    Result {i+1}: {result.get('result', 'N/A')} (confidence: {result.get('confidence', 'N/A')})")
                        else:
                            print(f"  Failed to get results: {results_response.status_code}")
                    except Exception as e:
                        print(f"  Error getting results: {e}")
                        
                else:
                    print(f"Failed to check status for task {task_id}: {response.status_code}")
                        
            except Exception as e:
                print(f"Failed to check status for task {task_id}: {e}")
    
    def print_results(self) -> None:
        """Print comprehensive test results"""
        self.print_header("Stress Test Results")
        
        if not self.system_metrics:
            print("No metrics available")
            return
        
        metrics = self.system_metrics[0]
        
        print(f"Test Duration: {self.end_time - self.start_time}")
        print(f"Total Sessions: {metrics.total_sessions}")
        print(f"Total Tasks Completed: {metrics.total_tasks_completed}")
        print(f"Total Errors: {metrics.total_errors}")
        print(f"Success Rate: {(metrics.total_tasks_completed / (metrics.total_tasks_completed + metrics.total_errors) * 100):.2f}%")
        print(f"Average Response Time: {metrics.avg_response_time_ms:.2f}ms")
        print(f"Average Task Completion Time: {metrics.avg_task_completion_time_ms:.2f}ms")
        
        print(f"\nTask Status Summary:")
        print(f"  Tasks Completed: {metrics.tasks_completed}")
        print(f"  Tasks In Progress: {metrics.tasks_in_progress}")
        print(f"  Tasks Failed: {metrics.tasks_failed}")
        
        print(f"\nConsensus Results:")
        print(f"  Consensus Reached: {metrics.consensus_reached_count}")
        print(f"  Positive Consensus: {metrics.positive_consensus_count}")
        print(f"  Negative Consensus: {metrics.negative_consensus_count}")
        print(f"  Ambiguous Consensus: {metrics.ambiguous_consensus_count}")
        
        # Print error summary
        if self.test_results:
            failed_results = [r for r in self.test_results if not r.success]
            if failed_results:
                print(f"\nError Summary:")
                error_types = {}
                for result in failed_results:
                    error_type = type(result.error_message).__name__ if result.error_message else "Unknown"
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                for error_type, count in error_types.items():
                    print(f"  {error_type}: {count} occurrences")
        
        # Save results to file
        self.save_results_to_file()
    
    def save_results_to_file(self) -> None:
        """Save test results to a JSON file"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_results_{timestamp}.json"
        
        results_data = {
            "test_config": {
                "iterations": self.iterations,
                "concurrent": self.concurrent,
                "tasks_per_session": self.tasks_per_session
            },
            "test_duration": str(self.end_time - self.start_time),
            "system_metrics": [vars(m) for m in self.system_metrics],
            "test_results": [vars(r) for r in self.test_results],
            "provider_id": self.provider_id,
            "task_ids": self.task_ids
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        print(f"\nResults saved to: {filename}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HotLabel System Stress Test")
    parser.add_argument("--iterations", type=int, default=10, help="Number of sessions to run")
    parser.add_argument("--concurrent", type=int, default=2, help="Number of concurrent sessions")
    parser.add_argument("--tasks-per-session", type=int, default=1, help="Number of tasks per session")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    
    args = parser.parse_args()
    
    print("HotLabel System Stress Test - Client SDK Perspective")
    print(f"Configuration:")
    print(f"  Iterations: {args.iterations}")
    print(f"  Concurrent sessions: {args.concurrent}")
    print(f"  Tasks per session: {args.tasks_per_session}")
    print(f"  Headless mode: {args.headless}")
    
    # Create and run stress test
    stress_test = HotLabelStressTest(
        iterations=args.iterations,
        concurrent=args.concurrent,
        tasks_per_session=args.tasks_per_session
    )
    
    try:
        stress_test.run_stress_test()
        stress_test.print_results()
    except KeyboardInterrupt:
        print("\nStress test interrupted by user")
    except Exception as e:
        print(f"Stress test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 