#!/usr/bin/env python3
"""
HotLabel System Stress Test - Multiprocessing Version
This script uses existing tasks from the database (created by pull_TII_all_categories.py)
"""

import requests
import uuid
import json
import time
import random
import argparse
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import sys
import os
from enum import Enum
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import statistics

# Playwright imports
from playwright.sync_api import sync_playwright, Page, Browser

# Configuration
KONG_URL = "http://192.168.8.16:8000"
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
TASKS_SERVICE_URL = "http://192.168.8.16:8002"  # Direct tasks service URL
SAMPLE_SITE_URL = "http://192.168.8.16:5001"

class TaskScenario(Enum):
    VQA_POSITIVE_CONSENSUS = "vqa_positive_consensus"
    VQA_NEGATIVE_CONSENSUS = "vqa_negative_consensus"
    VQA_AMBIGUOUS_CONSENSUS = "vqa_ambiguous_consensus"

@dataclass
class TestResult:
    session_id: str
    task_id: str
    scenario: str
    start_time: datetime
    end_time: datetime
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    hotlabel_modal_found: bool = False
    hotlabel_tasks_completed: int = 0
    page_title: Optional[str] = None
    page_url: Optional[str] = None

def complete_task_worker(args_tuple):
    """Worker function for multiprocessing"""
    (session_index, task_id, scenario, browserless_url) = args_tuple
    
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
    
    browser = None
    page = None
    playwright = None
    
    try:
        print(f"    [Session {session_index}] Starting task {task_id} ({scenario.value})")
        
        # Initialize Playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(browserless_url)
        page = browser.new_page()
        
        # Set viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # Navigate to sample site
        print(f"    [Session {session_index}] Navigating to {SAMPLE_SITE_URL}")
        page.goto(SAMPLE_SITE_URL, wait_until="networkidle")
        
        # Wait for page load and check for HotLabel modal
        time.sleep(5)
        
        result.page_title = page.title()
        result.page_url = page.url
        print(f"    [Session {session_index}] Page title: {result.page_title}")
        print(f"    [Session {session_index}] URL: {result.page_url}")
        
        # Check for HotLabel modal
        hotlabel_tasks_completed = check_hotlabel_modal(page, session_index)
        result.hotlabel_tasks_completed = hotlabel_tasks_completed
        result.hotlabel_modal_found = hotlabel_tasks_completed > 0
        print(f"    [Session {session_index}] HotLabel tasks completed: {hotlabel_tasks_completed}")
        
        # Complete quiz flow
        complete_quiz_flow(page, session_index)
        
        # Check for HotLabel modal again on result page
        time.sleep(3)
        hotlabel_tasks_completed += check_hotlabel_modal(page, session_index)
        result.hotlabel_tasks_completed = hotlabel_tasks_completed
        result.hotlabel_modal_found = result.hotlabel_modal_found or hotlabel_tasks_completed > 0
        
        # Success
        end_time = datetime.utcnow()
        result.end_time = end_time
        result.success = True
        result.response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        print(f"    [Session {session_index}] Successfully completed task {task_id}")
        return result
        
    except Exception as e:
        end_time = datetime.utcnow()
        result.end_time = end_time
        result.success = False
        result.error_message = str(e)
        result.response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        print(f"    [Session {session_index}] Failed: {e}")
        return result
        
    finally:
        if page:
            try:
                page.close()
            except:
                pass
        if browser:
            try:
                browser.close()
            except:
                pass
        if playwright:
            try:
                playwright.stop()
            except:
                pass

def check_hotlabel_modal(page: Page, session_index: int) -> int:
    """Check for HotLabel modal and complete tasks if found"""
    tasks_completed = 0
    
    try:
        # Look for HotLabel modal
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
                modal = page.wait_for_selector(selector, timeout=3000)
                if modal:
                    print(f"      [Session {session_index}] Found HotLabel modal: {selector}")
                    modal_found = True
                    break
            except:
                continue
        
        if not modal_found:
            print(f"      [Session {session_index}] No HotLabel modal found")
            return tasks_completed
        
        # Look for VQA options
        option_selectors = [
            "button[data-option-index]",
            "button:has-text('True')",
            "button:has-text('False')",
            ".hotlabel-options button"
        ]
        
        for selector in option_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"      [Session {session_index}] Found {len(elements)} options with {selector}")
                    # Click first option
                    elements[0].click()
                    time.sleep(2)
                    tasks_completed += 1
                    print(f"      [Session {session_index}] Clicked option, task completed")
                    break
            except Exception as e:
                print(f"      [Session {session_index}] Error with selector {selector}: {e}")
                continue
        
    except Exception as e:
        print(f"      [Session {session_index}] Error checking HotLabel modal: {e}")
    
    return tasks_completed

def complete_quiz_flow(page: Page, session_index: int):
    """Complete the quiz flow on the page"""
    try:
        # Look for Start Quiz button
        start_button_selectors = [
            "button:has-text('Start Quiz')",
            "button[type='submit']",
            "a:has-text('Start Quiz')"
        ]
        
        for selector in start_button_selectors:
            try:
                button = page.wait_for_selector(selector, timeout=3000)
                if button:
                    print(f"      [Session {session_index}] Found start button: {selector}")
                    button.click()
                    break
            except:
                continue
        
        # Wait for quiz page to load
        time.sleep(3)
        
        # Complete quiz questions
        quiz_selectors = [
            "input[type='radio']",
            "input[type='checkbox']",
            "select",
            "textarea"
        ]
        
        for selector in quiz_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element.is_visible() and element.is_enabled():
                        # Get tag name using evaluate method
                        tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                        element_type = element.get_attribute("type")
                        
                        if tag_name == "input" and element_type == "radio":
                            element.click()
                        elif tag_name == "input" and element_type == "checkbox":
                            element.click()
                        elif tag_name == "select":
                            options = element.query_selector_all("option")
                            if options:
                                options[0].click()
                        elif tag_name == "textarea":
                            element.fill("Test response")
            except Exception as e:
                print(f"      [Session {session_index}] Error with quiz selector {selector}: {e}")
                continue
        
        # Submit quiz
        submit_selectors = [
            "button:has-text('Submit')",
            "button[type='submit']",
            "input[type='submit']"
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = page.wait_for_selector(selector, timeout=3000)
                if submit_button:
                    print(f"      [Session {session_index}] Found submit button: {selector}")
                    submit_button.click()
                    break
            except:
                continue
        
        # Wait for result page
        time.sleep(3)
        
    except Exception as e:
        print(f"      [Session {session_index}] Error completing quiz flow: {e}")

def setup_test_environment():
    """Set up the test environment with existing tasks"""
    print("Setting up test environment...")
    
    # Get existing tasks from database
    response = requests.get(f"{TASKS_SERVICE_URL}/api/v1/tasks", headers={"X-API-Key": "internal-service"})
    if response.status_code >= 300:
        raise Exception(f"Failed to get existing tasks: {response.text}")
        
    tasks = response.json().get("items", [])
    print(f"Found {len(tasks)} existing tasks in the database")
    
    # Filter for pending tasks only
    assigned_tasks = [task for task in tasks if task.get("status") == "assigned"]
    print(f"Found {len(assigned_tasks)} assigned tasks available for testing")
    
    if not assigned_tasks:
        raise Exception("No assigned tasks found. Please run pull_TII_all_categories.py first.")
    
    # Select tasks for testing
    selected_tasks = assigned_tasks[:min(10, len(assigned_tasks))]  # Use up to 10 tasks
    
    task_ids = []
    scenario_results = {}
    
    for task in selected_tasks:
        task_ids.append(task["id"])
        # Assign scenario based on task type
        if task.get("task_type") == "true-false":
            scenario_results[task["id"]] = TaskScenario.VQA_POSITIVE_CONSENSUS
        elif task.get("task_type") == "numeric":
            scenario_results[task["id"]] = TaskScenario.VQA_NEGATIVE_CONSENSUS
        elif task.get("task_type") == "mcq":
            scenario_results[task["id"]] = TaskScenario.VQA_AMBIGUOUS_CONSENSUS
        else:
            scenario_results[task["id"]] = TaskScenario.VQA_POSITIVE_CONSENSUS
    
    print(f"Selected {len(selected_tasks)} tasks for stress testing:")
    for task in selected_tasks:
        print(f"  - Task ID: {task['id']}, Type: {task.get('task_type')}, Category: {task.get('category')}")
    
    return task_ids, scenario_results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HotLabel System Stress Test - Multiprocessing")
    parser.add_argument("--iterations", type=int, default=20, help="Number of test iterations")
    parser.add_argument("--concurrent", type=int, default=4, help="Number of concurrent processes")
    parser.add_argument("--browserless-url", type=str, default="ws://localhost:3000", help="Browserless WebSocket URL")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" HOTLABEL STRESS TEST - MULTIPROCESSING VERSION ".center(80, "="))
    print("This test uses existing tasks from the database (created by pull_TII_all_categories.py)")
    print("=" * 80)
    
    try:
        # Set up test environment
        task_ids, scenario_results = setup_test_environment()
        
        if not task_ids:
            print("ERROR: No tasks available for testing")
            sys.exit(1)
        
        print(f"\nRunning {args.iterations} iterations with {args.concurrent} concurrent processes...")
        print(f"Browserless URL: {args.browserless_url}")
        
        # Prepare arguments for worker processes
        worker_args = []
        for i in range(args.iterations):
            task_id = random.choice(task_ids)
            scenario = scenario_results.get(task_id, TaskScenario.VQA_POSITIVE_CONSENSUS)
            worker_args.append((i, task_id, scenario, args.browserless_url))
        
        # Run tests with multiprocessing
        results = []
        start_time = datetime.utcnow()
        
        with ProcessPoolExecutor(max_workers=args.concurrent) as executor:
            # Submit all tasks
            future_to_session = {
                executor.submit(complete_task_worker, args_tuple): args_tuple[0]
                for args_tuple in worker_args
            }
            
            # Collect results
            for future in as_completed(future_to_session):
                session_index = future_to_session[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"    [Session {session_index}] Completed: {result.success}")
                except Exception as e:
                    print(f"    [Session {session_index}] Failed: {e}")
        
        end_time = datetime.utcnow()
        
        # Calculate metrics
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        total_hotlabel_tasks = sum(r.hotlabel_tasks_completed for r in results)
        total_modal_found = sum(1 for r in results if r.hotlabel_modal_found)
        
        # Print results
        print("\n" + "=" * 80)
        print(" STRESS TEST RESULTS ".center(80, "="))
        print("=" * 80)
        
        print(f"Test Duration: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"Total Sessions: {len(results)}")
        print(f"Successful Sessions: {len(successful_results)}")
        print(f"Failed Sessions: {len(failed_results)}")
        print(f"Success Rate: {(len(successful_results) / len(results) * 100):.1f}%" if results else "N/A")
        
        if successful_results:
            avg_response_time = statistics.mean([r.response_time_ms for r in successful_results if r.response_time_ms])
            print(f"Average Response Time: {avg_response_time:.0f}ms")
        
        print(f"HotLabel Modals Found: {total_modal_found}")
        print(f"HotLabel Tasks Completed: {total_hotlabel_tasks}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"headless_stress_test_mp_results_{timestamp}.json"
        
        results_data = {
            "test_config": {
                "iterations": args.iterations,
                "concurrent": args.concurrent,
                "browserless_url": args.browserless_url
            },
            "test_duration": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds()
            },
            "results": [
                {
                    "session_id": r.session_id,
                    "task_id": r.task_id,
                    "scenario": r.scenario,
                    "success": r.success,
                    "response_time_ms": r.response_time_ms,
                    "hotlabel_modal_found": r.hotlabel_modal_found,
                    "hotlabel_tasks_completed": r.hotlabel_tasks_completed,
                    "page_title": r.page_title,
                    "page_url": r.page_url,
                    "error_message": r.error_message
                }
                for r in results
            ],
            "summary": {
                "total_sessions": len(results),
                "successful_sessions": len(successful_results),
                "failed_sessions": len(failed_results),
                "success_rate": len(successful_results) / len(results) if results else 0,
                "total_hotlabel_tasks": total_hotlabel_tasks,
                "total_modal_found": total_modal_found
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 