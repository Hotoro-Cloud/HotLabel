#!/usr/bin/env python3
"""
HotLabel System Stress Test - Confidence Scenarios
Tests various confidence measurement scenarios across sessions
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
KONG_URL = "http://localhost:8000"
TASKS_API_URL = f"{KONG_URL}/api/v1/tasks"
TASKS_SERVICE_URL = "http://localhost:8002"  # Direct tasks service URL
SAMPLE_SITE_URL = "http://localhost:5001"

class ConfidenceScenario(Enum):
    HIGH_INTERACTION = "high_interaction"  # Complex mouse movements, long hover times
    LOW_INTERACTION = "low_interaction"    # Simple movements, quick decisions
    MEDIUM_INTERACTION = "medium_interaction"  # Balanced interaction
    RAPID_RESPONSE = "rapid_response"      # Very fast responses
    SLOW_CAREFUL = "slow_careful"          # Very slow, careful responses
    BOT_LIKE = "bot_like"                  # Linear movements, no hover
    HUMAN_LIKE = "human_like"              # Natural human-like patterns

@dataclass
class ConfidenceTestResult:
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
    confidence_score: Optional[float] = None
    interaction_data: Optional[Dict] = None
    task_result_id: Optional[str] = None
    consensus_status: Optional[str] = None

def simulate_confidence_scenario(page: Page, scenario: ConfidenceScenario, session_index: int):
    """Simulate different confidence scenarios through user interaction patterns"""
    
    print(f"      [Session {session_index}] Simulating {scenario.value} scenario")
    
    if scenario == ConfidenceScenario.HIGH_INTERACTION:
        # Complex mouse movements, multiple hovers, long consideration
        simulate_complex_mouse_movements(page, session_index)
        simulate_multiple_hovers(page, session_index, hover_count=3, avg_duration=2000)
        time.sleep(random.uniform(3, 5))  # Long consideration time
        
    elif scenario == ConfidenceScenario.LOW_INTERACTION:
        # Simple movements, quick decisions
        simulate_simple_mouse_movements(page, session_index)
        simulate_quick_hover(page, session_index, duration=500)
        time.sleep(random.uniform(0.5, 1.5))  # Quick decision
        
    elif scenario == ConfidenceScenario.MEDIUM_INTERACTION:
        # Balanced interaction
        simulate_balanced_mouse_movements(page, session_index)
        simulate_multiple_hovers(page, session_index, hover_count=2, avg_duration=1000)
        time.sleep(random.uniform(1.5, 3))  # Medium consideration
        
    elif scenario == ConfidenceScenario.RAPID_RESPONSE:
        # Very fast responses
        simulate_quick_mouse_movement(page, session_index)
        time.sleep(random.uniform(0.2, 0.8))  # Very quick
        
    elif scenario == ConfidenceScenario.SLOW_CAREFUL:
        # Very slow, careful responses
        simulate_careful_mouse_movements(page, session_index)
        simulate_multiple_hovers(page, session_index, hover_count=4, avg_duration=3000)
        time.sleep(random.uniform(5, 8))  # Very long consideration
        
    elif scenario == ConfidenceScenario.BOT_LIKE:
        # Linear movements, no hover, robotic behavior
        simulate_linear_mouse_movements(page, session_index)
        time.sleep(random.uniform(0.1, 0.5))  # Very quick, bot-like
        
    elif scenario == ConfidenceScenario.HUMAN_LIKE:
        # Natural human-like patterns
        simulate_human_like_movements(page, session_index)
        simulate_natural_hovers(page, session_index)
        time.sleep(random.uniform(2, 4))  # Natural consideration time

def simulate_complex_mouse_movements(page: Page, session_index: int):
    """Simulate complex, human-like mouse movements"""
    print(f"        [Session {session_index}] Simulating complex mouse movements")
    
    # Get viewport size
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Create complex path with multiple direction changes
    points = [
        (width * 0.2, height * 0.3),
        (width * 0.4, height * 0.2),
        (width * 0.6, height * 0.4),
        (width * 0.5, height * 0.6),
        (width * 0.3, height * 0.5),
        (width * 0.7, height * 0.7)
    ]
    
    for i, (x, y) in enumerate(points):
        # Add some randomness to make it more human-like
        x += random.uniform(-20, 20)
        y += random.uniform(-20, 20)
        
        # Move mouse with variable speed
        duration = random.uniform(100, 300)
        page.mouse.move(x, y)
        time.sleep(duration / 1000)

def simulate_simple_mouse_movements(page: Page, session_index: int):
    """Simulate simple, direct mouse movements"""
    print(f"        [Session {session_index}] Simulating simple mouse movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Simple direct path
    start_x, start_y = width * 0.1, height * 0.1
    end_x, end_y = width * 0.8, height * 0.8
    
    page.mouse.move(start_x, start_y)
    time.sleep(0.1)
    page.mouse.move(end_x, end_y)
    time.sleep(0.1)

def simulate_balanced_mouse_movements(page: Page, session_index: int):
    """Simulate balanced mouse movements"""
    print(f"        [Session {session_index}] Simulating balanced mouse movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Moderate complexity path
    points = [
        (width * 0.3, height * 0.4),
        (width * 0.5, height * 0.3),
        (width * 0.7, height * 0.5)
    ]
    
    for x, y in points:
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.1, 0.3))

def simulate_quick_mouse_movement(page: Page, session_index: int):
    """Simulate very quick mouse movement"""
    print(f"        [Session {session_index}] Simulating quick mouse movement")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Very quick direct movement
    page.mouse.move(width * 0.5, height * 0.5)
    time.sleep(0.05)

def simulate_careful_mouse_movements(page: Page, session_index: int):
    """Simulate careful, precise mouse movements"""
    print(f"        [Session {session_index}] Simulating careful mouse movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Very careful, precise movements
    points = [
        (width * 0.2, height * 0.3),
        (width * 0.25, height * 0.35),
        (width * 0.3, height * 0.4),
        (width * 0.35, height * 0.45),
        (width * 0.4, height * 0.5)
    ]
    
    for x, y in points:
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.3, 0.6))  # Slow, careful movements

def simulate_linear_mouse_movements(page: Page, session_index: int):
    """Simulate linear, robotic mouse movements"""
    print(f"        [Session {session_index}] Simulating linear mouse movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Linear, robotic path
    start_x, start_y = width * 0.1, height * 0.1
    end_x, end_y = width * 0.9, height * 0.9
    
    # Move in straight line with constant speed
    steps = 10
    for i in range(steps + 1):
        x = start_x + (end_x - start_x) * i / steps
        y = start_y + (end_y - start_y) * i / steps
        page.mouse.move(x, y)
        time.sleep(0.05)  # Constant speed

def simulate_human_like_movements(page: Page, session_index: int):
    """Simulate natural human-like mouse movements"""
    print(f"        [Session {session_index}] Simulating human-like mouse movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Natural human-like path with slight curves and variations
    points = [
        (width * 0.2, height * 0.3),
        (width * 0.35, height * 0.25),
        (width * 0.5, height * 0.35),
        (width * 0.65, height * 0.45),
        (width * 0.8, height * 0.6)
    ]
    
    for i, (x, y) in enumerate(points):
        # Add natural variation
        x += random.uniform(-15, 15)
        y += random.uniform(-15, 15)
        
        # Variable speed like human movement
        duration = random.uniform(0.1, 0.4)
        page.mouse.move(x, y)
        time.sleep(duration)

def simulate_multiple_hovers(page: Page, session_index: int, hover_count: int, avg_duration: int):
    """Simulate multiple hover actions"""
    print(f"        [Session {session_index}] Simulating {hover_count} hovers")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    for i in range(hover_count):
        # Random position for hover
        x = random.uniform(width * 0.2, width * 0.8)
        y = random.uniform(height * 0.2, height * 0.8)
        
        page.mouse.move(x, y)
        duration = random.uniform(avg_duration * 0.5, avg_duration * 1.5)
        time.sleep(duration / 1000)

def simulate_quick_hover(page: Page, session_index: int, duration: int):
    """Simulate a quick hover action"""
    print(f"        [Session {session_index}] Simulating quick hover")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    x = random.uniform(width * 0.3, width * 0.7)
    y = random.uniform(height * 0.3, height * 0.7)
    
    page.mouse.move(x, y)
    time.sleep(duration / 1000)

def simulate_natural_hovers(page: Page, session_index: int):
    """Simulate natural hover patterns"""
    print(f"        [Session {session_index}] Simulating natural hovers")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Natural hover pattern - 1-3 hovers with varying durations
    hover_count = random.randint(1, 3)
    for i in range(hover_count):
        x = random.uniform(width * 0.2, width * 0.8)
        y = random.uniform(height * 0.2, height * 0.8)
        
        page.mouse.move(x, y)
        duration = random.uniform(500, 2000)  # 0.5 to 2 seconds
        time.sleep(duration / 1000)

def complete_task_worker(args_tuple):
    """Worker function for multiprocessing"""
    (session_index, task_id, scenario, browserless_url) = args_tuple
    
    session_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    result = ConfidenceTestResult(
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
        print(f"    [Session {session_index}] Starting confidence test for task {task_id} ({scenario.value})")
        
        # Initialize Playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(browserless_url)
        page = browser.new_page()
        
        # Set viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # Navigate to sample site
        print(f"    [Session {session_index}] Navigating to {SAMPLE_SITE_URL}")
        page.goto(SAMPLE_SITE_URL, wait_until="networkidle")
        
        # Wait for page load
        time.sleep(5)
        
        result.page_title = page.title()
        result.page_url = page.url
        print(f"    [Session {session_index}] Page title: {result.page_title}")
        print(f"    [Session {session_index}] URL: {result.page_url}")
        
        # Simulate confidence scenario before completing tasks
        simulate_confidence_scenario(page, scenario, session_index)
        
        # Check for HotLabel modal and complete tasks
        hotlabel_tasks_completed, task_result_id = check_hotlabel_modal_with_confidence(page, session_index, scenario)
        result.hotlabel_tasks_completed = hotlabel_tasks_completed
        result.hotlabel_modal_found = hotlabel_tasks_completed > 0
        result.task_result_id = task_result_id
        
        print(f"    [Session {session_index}] HotLabel tasks completed: {hotlabel_tasks_completed}")
        
        # Complete quiz flow
        complete_quiz_flow(page, session_index)
        
        # Check for HotLabel modal again on result page
        time.sleep(3)
        additional_tasks, additional_result_id = check_hotlabel_modal_with_confidence(page, session_index, scenario)
        result.hotlabel_tasks_completed += additional_tasks
        result.hotlabel_modal_found = result.hotlabel_modal_found or additional_tasks > 0
        if additional_result_id:
            result.task_result_id = additional_result_id
        
        # Success
        end_time = datetime.utcnow()
        result.end_time = end_time
        result.success = True
        result.response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Calculate confidence score based on scenario
        result.confidence_score = calculate_confidence_score(scenario)
        
        print(f"    [Session {session_index}] Successfully completed confidence test")
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

def check_hotlabel_modal_with_confidence(page: Page, session_index: int, scenario: ConfidenceScenario) -> Tuple[int, Optional[str]]:
    """Check for HotLabel modal and complete tasks with confidence simulation"""
    tasks_completed = 0
    task_result_id = None
    
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
            return tasks_completed, task_result_id
        
        # Simulate confidence scenario before selecting options
        simulate_confidence_scenario(page, scenario, session_index)
        
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
                    
                    # Simulate confidence-based selection
                    selected_option = select_option_with_confidence(page, elements, scenario, session_index)
                    if selected_option:
                        tasks_completed += 1
                        print(f"      [Session {session_index}] Selected option with confidence: {selected_option}")
                        
                        # Extract task result ID if available
                        task_result_id = extract_task_result_id(page, session_index)
                        break
            except Exception as e:
                print(f"      [Session {session_index}] Error with selector {selector}: {e}")
                continue
        
    except Exception as e:
        print(f"      [Session {session_index}] Error checking HotLabel modal: {e}")
    
    return tasks_completed, task_result_id

def select_option_with_confidence(page: Page, elements: List, scenario: ConfidenceScenario, session_index: int) -> Optional[str]:
    """Select an option with confidence-based behavior"""
    try:
        if not elements:
            return None
        
        # Simulate confidence-based decision making
        if scenario == ConfidenceScenario.HIGH_INTERACTION:
            # High interaction - hover over multiple options before selecting
            for i, element in enumerate(elements[:2]):  # Hover over first 2 options
                element.hover()
                time.sleep(random.uniform(0.5, 1.5))
            
            # Select first option with high confidence
            elements[0].click()
            return "True"
            
        elif scenario == ConfidenceScenario.LOW_INTERACTION:
            # Low interaction - quick selection
            elements[0].click()
            return "True"
            
        elif scenario == ConfidenceScenario.RAPID_RESPONSE:
            # Rapid response - very quick selection
            elements[0].click()
            return "True"
            
        elif scenario == ConfidenceScenario.SLOW_CAREFUL:
            # Slow careful - hover extensively before selecting
            for element in elements:
                element.hover()
                time.sleep(random.uniform(1, 2))
            
            # Select second option if available
            if len(elements) > 1:
                elements[1].click()
                return "False"
            else:
                elements[0].click()
                return "True"
                
        elif scenario == ConfidenceScenario.BOT_LIKE:
            # Bot-like - immediate selection without hover
            elements[0].click()
            return "True"
            
        elif scenario == ConfidenceScenario.HUMAN_LIKE:
            # Human-like - natural selection pattern
            if len(elements) > 1:
                # Hover over both options briefly
                elements[0].hover()
                time.sleep(random.uniform(0.3, 0.8))
                elements[1].hover()
                time.sleep(random.uniform(0.3, 0.8))
                
                # Select based on scenario
                choice = random.choice([0, 1])
                elements[choice].click()
                return "True" if choice == 0 else "False"
            else:
                elements[0].click()
                return "True"
        
        else:  # MEDIUM_INTERACTION
            # Medium interaction - balanced approach
            if len(elements) > 1:
                elements[0].hover()
                time.sleep(random.uniform(0.5, 1.0))
                elements[0].click()
                return "True"
            else:
                elements[0].click()
                return "True"
                
    except Exception as e:
        print(f"      [Session {session_index}] Error selecting option: {e}")
    
    return None

def extract_task_result_id(page: Page, session_index: int) -> Optional[str]:
    """Extract task result ID from the page if available"""
    try:
        # Look for task result ID in various locations
        result_selectors = [
            "[data-task-result-id]",
            "[data-result-id]",
            ".task-result-id",
            ".result-id"
        ]
        
        for selector in result_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    result_id = element.get_attribute("data-task-result-id") or element.get_attribute("data-result-id") or element.text_content()
                    if result_id:
                        print(f"      [Session {session_index}] Found task result ID: {result_id}")
                        return result_id.strip()
            except:
                continue
        
        return None
        
    except Exception as e:
        print(f"      [Session {session_index}] Error extracting task result ID: {e}")
        return None

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
                        if element.tag_name == "input" and element.get_attribute("type") == "radio":
                            element.click()
                        elif element.tag_name == "input" and element.get_attribute("type") == "checkbox":
                            element.click()
                        elif element.tag_name == "select":
                            options = element.query_selector_all("option")
                            if options:
                                options[0].click()
                        elif element.tag_name == "textarea":
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

def calculate_confidence_score(scenario: ConfidenceScenario) -> float:
    """Calculate confidence score based on scenario"""
    if scenario == ConfidenceScenario.HIGH_INTERACTION:
        return random.uniform(0.8, 0.95)  # High confidence
    elif scenario == ConfidenceScenario.LOW_INTERACTION:
        return random.uniform(0.4, 0.7)   # Low confidence
    elif scenario == ConfidenceScenario.MEDIUM_INTERACTION:
        return random.uniform(0.6, 0.8)   # Medium confidence
    elif scenario == ConfidenceScenario.RAPID_RESPONSE:
        return random.uniform(0.3, 0.6)   # Low confidence (quick decisions)
    elif scenario == ConfidenceScenario.SLOW_CAREFUL:
        return random.uniform(0.9, 1.0)   # Very high confidence
    elif scenario == ConfidenceScenario.BOT_LIKE:
        return random.uniform(0.1, 0.4)   # Very low confidence (bot-like)
    elif scenario == ConfidenceScenario.HUMAN_LIKE:
        return random.uniform(0.7, 0.9)   # High confidence (human-like)
    else:
        return random.uniform(0.5, 0.8)   # Default medium confidence

def retrieve_task_results(task_ids: List[str]) -> Dict[str, Any]:
    """Retrieve task results and consensus status"""
    print("\n--- Retrieving Task Results ---")
    
    results = {}
    for task_id in task_ids:
        try:
            response = requests.get(f"{TASKS_API_URL}/{task_id}")
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("status", "unknown")
                results_count = len(task_data.get("results", []))
                
                results[task_id] = {
                    "status": status,
                    "results_count": results_count,
                    "consensus_reached": status == "COMPLETED",
                    "final_answer": task_data.get("final_answer"),
                    "confidence": task_data.get("confidence"),
                    "agreement_rate": task_data.get("agreement_rate")
                }
                
                print(f"Task {task_id}: {status} ({results_count} results)")
                
                if status == "COMPLETED":
                    print(f"  Final Answer: {task_data.get('final_answer')}")
                    print(f"  Confidence: {task_data.get('confidence')}")
                    print(f"  Agreement Rate: {task_data.get('agreement_rate')}")
                    
        except Exception as e:
            print(f"Error retrieving results for task {task_id}: {e}")
            results[task_id] = {"error": str(e)}
    
    return results

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
    pending_tasks = [task for task in tasks if task.get("status") == "PENDING"]
    print(f"Found {len(pending_tasks)} pending tasks available for testing")
    
    if not pending_tasks:
        raise Exception("No pending tasks found. Please run pull_TII_all_categories.py first.")
    
    # Select tasks for testing
    selected_tasks = pending_tasks[:min(10, len(pending_tasks))]  # Use up to 10 tasks
    
    task_ids = []
    scenario_results = {}
    
    for task in selected_tasks:
        task_ids.append(task["id"])
        # Assign scenario based on task type
        if task.get("task_type") == "true-false":
            scenario_results[task["id"]] = ConfidenceScenario.HIGH_INTERACTION
        elif task.get("task_type") == "numeric":
            scenario_results[task["id"]] = ConfidenceScenario.MEDIUM_INTERACTION
        elif task.get("task_type") == "mcq":
            scenario_results[task["id"]] = ConfidenceScenario.LOW_INTERACTION
        else:
            scenario_results[task["id"]] = ConfidenceScenario.HUMAN_LIKE
    
    print(f"Selected {len(selected_tasks)} tasks for confidence testing:")
    for task in selected_tasks:
        print(f"  - Task ID: {task['id']}, Type: {task.get('task_type')}, Category: {task.get('category')}")
    
    return task_ids, scenario_results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HotLabel System Stress Test - Confidence Scenarios")
    parser.add_argument("--iterations", type=int, default=30, help="Number of test iterations")
    parser.add_argument("--concurrent", type=int, default=6, help="Number of concurrent processes")
    parser.add_argument("--browserless-url", type=str, default="ws://localhost:3000", help="Browserless WebSocket URL")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" HOTLABEL STRESS TEST - CONFIDENCE SCENARIOS ".center(80, "="))
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
        scenarios = list(ConfidenceScenario)
        
        for i in range(args.iterations):
            task_id = random.choice(task_ids)
            scenario = random.choice(scenarios)  # Random confidence scenario
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
                    print(f"    [Session {session_index}] Completed: {result.success} (scenario: {result.scenario})")
                except Exception as e:
                    print(f"    [Session {session_index}] Failed: {e}")
        
        end_time = datetime.utcnow()
        
        # Calculate metrics
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        total_hotlabel_tasks = sum(r.hotlabel_tasks_completed for r in results)
        total_modal_found = sum(1 for r in results if r.hotlabel_modal_found)
        
        # Group results by scenario
        scenario_stats = {}
        for scenario in ConfidenceScenario:
            scenario_results_list = [r for r in results if r.scenario == scenario.value]
            if scenario_results_list:
                scenario_stats[scenario.value] = {
                    "count": len(scenario_results_list),
                    "successful": len([r for r in scenario_results_list if r.success]),
                    "avg_confidence": statistics.mean([r.confidence_score for r in scenario_results_list if r.confidence_score]) if scenario_results_list else 0
                }
        
        # Retrieve task results
        task_results = retrieve_task_results(task_ids)
        
        # Print results
        print("\n" + "=" * 80)
        print(" CONFIDENCE SCENARIOS TEST RESULTS ".center(80, "="))
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
        
        print(f"\nScenario Statistics:")
        for scenario, stats in scenario_stats.items():
            success_rate = (stats["successful"] / stats["count"] * 100) if stats["count"] > 0 else 0
            print(f"  {scenario}: {stats['count']} sessions, {stats['successful']} successful ({success_rate:.1f}%), avg confidence: {stats['avg_confidence']:.2f}")
        
        print(f"\nTask Results:")
        completed_tasks = sum(1 for result in task_results.values() if result.get("consensus_reached"))
        print(f"  Tasks with consensus reached: {completed_tasks}/{len(task_ids)}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"confidence_scenarios_test_results_{timestamp}.json"
        
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
                    "confidence_score": r.confidence_score,
                    "task_result_id": r.task_result_id,
                    "error_message": r.error_message
                }
                for r in results
            ],
            "scenario_statistics": scenario_stats,
            "task_results": task_results,
            "summary": {
                "total_sessions": len(results),
                "successful_sessions": len(successful_results),
                "failed_sessions": len(failed_results),
                "success_rate": len(successful_results) / len(results) if results else 0,
                "total_hotlabel_tasks": total_hotlabel_tasks,
                "total_modal_found": total_modal_found,
                "tasks_with_consensus": completed_tasks
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