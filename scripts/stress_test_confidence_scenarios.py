#!/usr/bin/env python3
"""
HotLabel System Stress Test - Confidence Scenarios
Tests various confidence measurement scenarios across sessions
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
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
SAMPLE_SITE_URL = "http://192.168.8.16:5001"

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
    
    # Perfectly linear movement (bot-like)
    start_x, start_y = width * 0.1, height * 0.1
    end_x, end_y = width * 0.9, height * 0.9
    
    steps = 10
    for i in range(steps + 1):
        x = start_x + (end_x - start_x) * i / steps
        y = start_y + (end_y - start_y) * i / steps
        page.mouse.move(x, y)
        time.sleep(0.05)  # Consistent timing

def simulate_human_like_movements(page: Page, session_index: int):
    """Simulate natural human-like mouse movements"""
    print(f"        [Session {session_index}] Simulating human-like movements")
    
    viewport = page.viewport_size
    width, height = viewport['width'], viewport['height']
    
    # Natural curve with slight variations
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
        
        # Variable speed like human
        duration = random.uniform(150, 400)
        page.mouse.move(x, y)
        time.sleep(duration / 1000)

def simulate_multiple_hovers(page: Page, session_index: int, hover_count: int, avg_duration: int):
    """Simulate multiple hover events on different elements"""
    print(f"        [Session {session_index}] Simulating {hover_count} hovers (avg {avg_duration}ms)")
    
    # Find all interactive elements
    selectors = [
        "button",
        ".hotlabel-option",
        "[data-option-index]",
        "input",
        "a"
    ]
    
    elements = []
    for selector in selectors:
        try:
            found_elements = page.query_selector_all(selector)
            elements.extend(found_elements)
        except:
            continue
    
    if not elements:
        print(f"        [Session {session_index}] No elements found for hovering")
        return
    
    # Simulate hovers on random elements
    for i in range(min(hover_count, len(elements))):
        element = random.choice(elements)
        try:
            # Hover over element
            element.hover()
            duration = random.uniform(avg_duration * 0.5, avg_duration * 1.5)
            time.sleep(duration / 1000)
            
            # Move away
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(0.2)
        except Exception as e:
            print(f"        [Session {session_index}] Error hovering: {e}")

def simulate_quick_hover(page: Page, session_index: int, duration: int):
    """Simulate a quick hover"""
    print(f"        [Session {session_index}] Simulating quick hover ({duration}ms)")
    
    # Find first available element
    selectors = ["button", ".hotlabel-option", "[data-option-index]"]
    
    for selector in selectors:
        try:
            element = page.query_selector(selector)
            if element:
                element.hover()
                time.sleep(duration / 1000)
                break
        except:
            continue

def simulate_natural_hovers(page: Page, session_index: int):
    """Simulate natural hover patterns"""
    print(f"        [Session {session_index}] Simulating natural hovers")
    
    # Find elements
    elements = page.query_selector_all("button, .hotlabel-option, [data-option-index]")
    
    if not elements:
        return
    
    # Natural hover pattern: 1-3 hovers with variable duration
    hover_count = random.randint(1, 3)
    
    for i in range(hover_count):
        element = random.choice(elements)
        try:
            element.hover()
            # Natural duration: 0.5 to 2 seconds
            duration = random.uniform(500, 2000)
            time.sleep(duration / 1000)
            
            # Natural pause between hovers
            if i < hover_count - 1:
                time.sleep(random.uniform(0.3, 1.0))
        except:
            continue 

def complete_task_worker(args_tuple):
    """Worker function for multiprocessing with confidence scenarios"""
    (session_index, task_id, scenario, browserless_url, provider_api_key) = args_tuple
    
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
        
        # Check for HotLabel modal and simulate confidence scenario
        hotlabel_tasks_completed, task_result_id = check_hotlabel_modal_with_confidence(
            page, session_index, scenario
        )
        result.hotlabel_tasks_completed = hotlabel_tasks_completed
        result.hotlabel_modal_found = hotlabel_tasks_completed > 0
        result.task_result_id = task_result_id
        print(f"    [Session {session_index}] HotLabel tasks completed: {hotlabel_tasks_completed}")
        
        # Complete quiz flow
        complete_quiz_flow(page, session_index)
        
        # Check for HotLabel modal again on result page
        time.sleep(3)
        additional_tasks, additional_result_id = check_hotlabel_modal_with_confidence(
            page, session_index, scenario
        )
        result.hotlabel_tasks_completed += additional_tasks
        result.hotlabel_modal_found = result.hotlabel_modal_found or additional_tasks > 0
        if additional_result_id:
            result.task_result_id = additional_result_id
        
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
        
        # Simulate confidence scenario before making selection
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
                    
                    # Simulate final interaction before clicking
                    if scenario in [ConfidenceScenario.HIGH_INTERACTION, ConfidenceScenario.SLOW_CAREFUL]:
                        # Additional consideration for high confidence scenarios
                        time.sleep(random.uniform(1, 2))
                    
                    # Click first option
                    elements[0].click()
                    time.sleep(2)
                    tasks_completed += 1
                    print(f"      [Session {session_index}] Clicked option, task completed")
                    
                    # Try to extract task result ID from network requests or page
                    task_result_id = extract_task_result_id(page, session_index)
                    break
            except Exception as e:
                print(f"      [Session {session_index}] Error with selector {selector}: {e}")
                continue
        
    except Exception as e:
        print(f"      [Session {session_index}] Error checking HotLabel modal: {e}")
    
    return tasks_completed, task_result_id

def extract_task_result_id(page: Page, session_index: int) -> Optional[str]:
    """Try to extract task result ID from the page or network requests"""
    try:
        # Check if there's any indication of task result ID in the page
        # This is a simplified approach - in a real scenario, you might need to
        # intercept network requests or check for specific elements
        
        # Look for any data attributes or elements that might contain result info
        result_elements = page.query_selector_all("[data-result-id], [data-task-result], .task-result")
        
        if result_elements:
            for element in result_elements:
                result_id = element.get_attribute("data-result-id") or element.get_attribute("data-task-result")
                if result_id:
                    print(f"        [Session {session_index}] Found task result ID: {result_id}")
                    return result_id
        
        # If no result ID found, return None
        return None
        
    except Exception as e:
        print(f"        [Session {session_index}] Error extracting task result ID: {e}")
        return None

def complete_quiz_flow(page: Page, session_index: int):
    """Complete the quiz flow"""
    try:
        # Look for Start Quiz button
        print(f"    [Session {session_index}] Looking for Start Quiz button...")
        start_button = page.wait_for_selector("button:has-text('Start Quiz')", timeout=10000)
        if start_button:
            print(f"    [Session {session_index}] Clicking Start Quiz...")
            start_button.click()
        
        # Wait for quiz page
        page.wait_for_selector("form", timeout=10000)
        print(f"    [Session {session_index}] Quiz page loaded")
        
        # Complete quiz questions
        radio_buttons = page.query_selector_all("input[type='radio']")
        questions = {}
        for radio in radio_buttons:
            name = radio.get_attribute("name")
            if name not in questions:
                questions[name] = []
            questions[name].append(radio)
        
        for question_name, radios in questions.items():
            if radios:
                selected_radio = random.choice(radios)
                selected_radio.click()
                time.sleep(0.5)
        
        # Submit quiz
        submit_button = page.wait_for_selector("button[type='submit']")
        submit_button.click()
        
        # Wait for result page
        page.wait_for_load_state("networkidle")
        print(f"    [Session {session_index}] Result page loaded")
        
    except Exception as e:
        print(f"    [Session {session_index}] Error in quiz flow: {e}") 

def retrieve_task_results(task_ids: List[str], provider_api_key: str) -> Dict[str, Any]:
    """Retrieve task results and consensus data"""
    print("\n" + "="*80)
    print("RETRIEVING TASK RESULTS AND CONSENSUS DATA")
    print("="*80)
    
    results_summary = {
        "task_results": {},
        "consensus_data": {},
        "confidence_analysis": {}
    }
    
    for task_id in task_ids:
        print(f"\n📊 Analyzing Task: {task_id}")
        
        try:
            # Get task results
            headers = {"X-API-Key": provider_api_key}
            response = requests.get(f"{TASKS_API_URL}/results/task/{task_id}", headers=headers)
            
            if response.status_code == 200:
                task_results = response.json()
                results_summary["task_results"][task_id] = task_results
                
                print(f"  ✅ Found {len(task_results)} task results")
                
                # Analyze confidence scores
                confidence_scores = []
                for result in task_results:
                    if "confidence" in result:
                        confidence_scores.append(result["confidence"])
                    if "result_metadata" in result and "confidence_calculation" in result["result_metadata"]:
                        calc = result["result_metadata"]["confidence_calculation"]
                        print(f"    📈 Confidence breakdown: {calc}")
                
                if confidence_scores:
                    avg_confidence = statistics.mean(confidence_scores)
                    min_confidence = min(confidence_scores)
                    max_confidence = max(confidence_scores)
                    
                    results_summary["confidence_analysis"][task_id] = {
                        "avg_confidence": avg_confidence,
                        "min_confidence": min_confidence,
                        "max_confidence": max_confidence,
                        "confidence_scores": confidence_scores
                    }
                    
                    print(f"    📊 Confidence Analysis:")
                    print(f"      Average: {avg_confidence:.3f}")
                    print(f"      Range: {min_confidence:.3f} - {max_confidence:.3f}")
                    print(f"      Scores: {[f'{c:.3f}' for c in confidence_scores]}")
                
                # Get consensus data
                try:
                    consensus_response = requests.get(f"{KONG_URL}/api/v1/consensus/{task_id}")
                    if consensus_response.status_code == 200:
                        consensus_data = consensus_response.json()
                        results_summary["consensus_data"][task_id] = consensus_data
                        
                        print(f"    🎯 Consensus Data:")
                        print(f"      Status: {consensus_data.get('status', 'N/A')}")
                        print(f"      Agreement Score: {consensus_data.get('agreement_score', 'N/A')}")
                        print(f"      Validator Count: {consensus_data.get('validator_count', 'N/A')}")
                    else:
                        print(f"    ⚠️  No consensus data available (Status: {consensus_response.status_code})")
                except Exception as e:
                    print(f"    ❌ Error retrieving consensus: {e}")
                
            else:
                print(f"  ❌ Failed to retrieve task results (Status: {response.status_code})")
                
        except Exception as e:
            print(f"  ❌ Error analyzing task {task_id}: {e}")
    
    return results_summary

def setup_test_environment():
    """Set up provider and tasks for confidence testing"""
    print("--- Setting up test environment for confidence scenarios ---")
    
    # Register provider
    provider_data = {
        "name": "Confidence Scenario Test Provider",
        "contact_email": f"confidence_test_provider_{uuid.uuid4().hex[:8]}@example.com",
        "description": "Provider for confidence scenario stress testing",
        "website": "https://example.com/confidence-test-provider"
    }
    
    response = requests.post(PROVIDERS_API_URL, json=provider_data)
    if response.status_code >= 300:
        raise Exception(f"Failed to register provider: {response.text}")
        
    result = response.json()
    provider_id = result["id"]
    provider_api_key = result["api_key"]
    print(f"Provider registered: {provider_id}")
    
    # Create tasks for different confidence scenarios
    task_ids = []
    scenario_results = {}
    
    scenarios = [
        ConfidenceScenario.HIGH_INTERACTION,
        ConfidenceScenario.LOW_INTERACTION,
        ConfidenceScenario.MEDIUM_INTERACTION,
        ConfidenceScenario.RAPID_RESPONSE,
        ConfidenceScenario.SLOW_CAREFUL,
        ConfidenceScenario.BOT_LIKE,
        ConfidenceScenario.HUMAN_LIKE
    ]
    
    for scenario in scenarios:
        base_data = {
            "title": f"Confidence Test - {scenario.value}",
            "description": f"Confidence test task for {scenario.value} scenario",
            "provider_id": provider_id,
            "task_type": "true-false",
            "category": "vqa",
            "complexity_level": 1,
            "topic": scenario.value,
            "agreement_threshold": 0.7,
            "confidence_threshold": 0.6,
            "status": "pending",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }
        
        task_data = {
            **base_data,
            "content": {
                "image_url": "https://s3-eu-north-1-derc-wmi-crowdlabel-production.s3.eu-north-1.amazonaws.com/tii_vqa_0whejvjm9blfgjb6.png",
                "image_filename": "tii_vqa_0whejvjm9blfgjb6.png",
                "question": f"Is this image suitable for {scenario.value} confidence testing?"
            },
            "task": {
                "text": f"Is this image suitable for {scenario.value} confidence testing?",
                "choices": [
                    {"key": "a", "value": "True"},
                    {"key": "b", "value": "False"}
                ]
            },
            "track_id": f"t-confidence-test-{scenario.value}"
        }
        
        headers = {"X-API-Key": provider_api_key}
        response = requests.post(TASKS_API_URL, json=task_data, headers=headers)
        
        if response.status_code >= 300:
            print(f"Failed to create task for {scenario.value}: {response.text}")
            continue
            
        result = response.json()
        task_id = str(result["id"])
        task_ids.append(task_id)
        scenario_results[task_id] = scenario
        
        print(f"Created task {task_id} for scenario {scenario.value}")
    
    return provider_id, provider_api_key, task_ids, scenario_results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HotLabel System Confidence Scenario Stress Test")
    parser.add_argument("--iterations", type=int, default=5, help="Number of sessions per scenario")
    parser.add_argument("--concurrent", type=int, default=2, help="Number of concurrent processes")
    parser.add_argument("--browserless-url", type=str, default="ws://localhost:3000", help="Browserless service URL")
    
    args = parser.parse_args()
    
    print("HotLabel System Confidence Scenario Stress Test")
    print(f"Configuration:")
    print(f"  Iterations per scenario: {args.iterations}")
    print(f"  Concurrent processes: {args.concurrent}")
    print(f"  Browserless URL: {args.browserless_url}")
    
    start_time = datetime.utcnow()
    
    try:
        # Set up test environment
        provider_id, provider_api_key, task_ids, scenario_results = setup_test_environment()
        
        print(f"\nCreated {len(task_ids)} tasks for confidence testing")
        print(f"Task IDs: {task_ids}")
        
        # Prepare arguments for multiprocessing
        args_list = []
        for i in range(args.iterations):
            # For each iteration, select one task from each scenario
            for scenario in ConfidenceScenario:
                scenario_task_ids = [tid for tid, s in scenario_results.items() if s == scenario]
                if scenario_task_ids:
                    task_id = random.choice(scenario_task_ids)
                    args_list.append((i + 1, task_id, scenario, args.browserless_url, provider_api_key))
        
        print(f"Prepared {len(args_list)} test sessions")
        
        # Run stress test with multiprocessing
        test_results = []
        with ProcessPoolExecutor(max_workers=args.concurrent) as executor:
            future_to_args = {executor.submit(complete_task_worker, args_tuple): args_tuple for args_tuple in args_list}
            
            for future in as_completed(future_to_args):
                args_tuple = future_to_args[future]
                session_index = args_tuple[0]
                scenario = args_tuple[2]
                try:
                    result = future.result()
                    test_results.append(result)
                    print(f"Completed session {session_index} ({scenario.value}): {'Success' if result.success else 'Failed'}")
                except Exception as e:
                    print(f"Session {session_index} ({scenario.value}) failed with exception: {e}")
                    failed_result = ConfidenceTestResult(
                        session_id=str(uuid.uuid4()),
                        task_id=args_tuple[1],
                        scenario=args_tuple[2].value,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        success=False,
                        error_message=str(e)
                    )
                    test_results.append(failed_result)
        
        # Calculate results by scenario
        scenario_stats = {}
        for scenario in ConfidenceScenario:
            scenario_results_list = [r for r in test_results if r.scenario == scenario.value]
            if scenario_results_list:
                successful = len([r for r in scenario_results_list if r.success])
                total = len(scenario_results_list)
                success_rate = (successful / total * 100) if total > 0 else 0
                avg_response_time = statistics.mean([r.response_time_ms for r in scenario_results_list if r.response_time_ms])
                
                scenario_stats[scenario.value] = {
                    "total": total,
                    "successful": successful,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "hotlabel_tasks_completed": sum([r.hotlabel_tasks_completed for r in scenario_results_list])
                }
        
        # Print comprehensive results
        end_time = datetime.utcnow()
        print("\n" + "="*80)
        print("CONFIDENCE SCENARIO STRESS TEST RESULTS")
        print("="*80)
        
        print(f"Test Duration: {end_time - start_time}")
        print(f"Total Sessions: {len(test_results)}")
        
        # Overall statistics
        successful_count = len([r for r in test_results if r.success])
        failed_count = len([r for r in test_results if not r.success])
        hotlabel_modals_found = len([r for r in test_results if r.hotlabel_modal_found])
        hotlabel_tasks_completed = sum([r.hotlabel_tasks_completed for r in test_results])
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Successful: {successful_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Success Rate: {(successful_count / len(test_results) * 100):.2f}%")
        print(f"  HotLabel Modals Found: {hotlabel_modals_found}")
        print(f"  HotLabel Tasks Completed: {hotlabel_tasks_completed}")
        
        # Scenario-specific results
        print(f"\n🎯 SCENARIO-SPECIFIC RESULTS:")
        for scenario_name, stats in scenario_stats.items():
            print(f"\n  {scenario_name.upper()}:")
            print(f"    Sessions: {stats['total']}")
            print(f"    Success Rate: {stats['success_rate']:.2f}%")
            print(f"    Avg Response Time: {stats['avg_response_time_ms']:.0f}ms")
            print(f"    Tasks Completed: {stats['hotlabel_tasks_completed']}")
        
        # Retrieve and display task results
        results_summary = retrieve_task_results(task_ids, provider_api_key)
        
        # Print confidence analysis summary
        if results_summary["confidence_analysis"]:
            print(f"\n📈 CONFIDENCE ANALYSIS SUMMARY:")
            for task_id, analysis in results_summary["confidence_analysis"].items():
                scenario = scenario_results.get(task_id, "Unknown")
                print(f"\n  Task {task_id} ({scenario.value}):")
                print(f"    Average Confidence: {analysis['avg_confidence']:.3f}")
                print(f"    Confidence Range: {analysis['min_confidence']:.3f} - {analysis['max_confidence']:.3f}")
                print(f"    Individual Scores: {[f'{c:.3f}' for c in analysis['confidence_scores']]}")
        
        # Print consensus summary
        if results_summary["consensus_data"]:
            print(f"\n🎯 CONSENSUS SUMMARY:")
            for task_id, consensus in results_summary["consensus_data"].items():
                scenario = scenario_results.get(task_id, "Unknown")
                print(f"\n  Task {task_id} ({scenario.value}):")
                print(f"    Status: {consensus.get('status', 'N/A')}")
                print(f"    Agreement Score: {consensus.get('agreement_score', 'N/A')}")
                print(f"    Validator Count: {consensus.get('validator_count', 'N/A')}")
        
        print(f"\n✅ Confidence scenario stress test completed successfully!")
        
    except Exception as e:
        print(f"Confidence scenario stress test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Set multiprocessing start method for macOS compatibility
    if sys.platform == "darwin":
        mp.set_start_method('spawn', force=True)
    
    main() 