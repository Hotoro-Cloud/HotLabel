#!/usr/bin/env python3
"""
HotLabel System Stress Test - Multiprocessing Version
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
PROVIDERS_API_URL = f"{KONG_URL}/api/v1/providers"
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
    (session_index, task_id, scenario, browserless_url, provider_api_key) = args_tuple
    
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

def setup_test_environment():
    """Set up provider and tasks"""
    print("--- Setting up test environment ---")
    
    # Register provider
    provider_data = {
        "name": "Headless Stress Test Provider (MP)",
        "contact_email": f"headless_stress_test_provider_mp_{uuid.uuid4().hex[:8]}@example.com",
        "description": "Provider for headless stress testing (multiprocessing)",
        "website": "https://example.com/headless-stress-test-provider-mp"
    }
    
    response = requests.post(PROVIDERS_API_URL, json=provider_data)
    if response.status_code >= 300:
        raise Exception(f"Failed to register provider: {response.text}")
        
    result = response.json()
    provider_id = result["id"]
    provider_api_key = result["api_key"]
    print(f"Provider registered: {provider_id}")
    
    # Create tasks
    task_ids = []
    scenario_results = {}
    
    scenarios = [
        TaskScenario.VQA_POSITIVE_CONSENSUS,
        TaskScenario.VQA_NEGATIVE_CONSENSUS,
        TaskScenario.VQA_AMBIGUOUS_CONSENSUS
    ]
    
    for scenario in scenarios:
        task_data = {
            "title": f"Headless Stress Test MP - {scenario.value}",
            "description": f"Headless stress test task for {scenario.value} scenario (multiprocessing)",
            "provider_id": provider_id,
            "task_type": "vqa",
            "category": "vqa",
            "complexity_level": 1,
            "type": "true-false",
            "topic": scenario.value.replace("vqa_", "").replace("_consensus", ""),
            "agreement_threshold": 0.7,
            "confidence_threshold": 0.6,
            "status": "pending",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
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
            "track_id": f"t-headless-stress-test-mp-{scenario.value}"
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
    parser = argparse.ArgumentParser(description="HotLabel System Headless Stress Test (Multiprocessing)")
    parser.add_argument("--iterations", type=int, default=10, help="Number of sessions to run")
    parser.add_argument("--concurrent", type=int, default=2, help="Number of concurrent processes")
    parser.add_argument("--tasks-per-session", type=int, default=1, help="Number of tasks per session")
    parser.add_argument("--browserless-url", type=str, default="ws://localhost:3000", help="Browserless service URL")
    
    args = parser.parse_args()
    
    print("HotLabel System Headless Stress Test - Multiprocessing")
    print(f"Configuration:")
    print(f"  Iterations: {args.iterations}")
    print(f"  Concurrent processes: {args.concurrent}")
    print(f"  Tasks per session: {args.tasks_per_session}")
    print(f"  Browserless URL: {args.browserless_url}")
    
    start_time = datetime.utcnow()
    
    try:
        # Set up test environment
        provider_id, provider_api_key, task_ids, scenario_results = setup_test_environment()
        
        print(f"Created {len(task_ids)} tasks for testing")
        print(f"Task IDs: {task_ids}")
        
        # Prepare arguments for multiprocessing
        args_list = []
        for i in range(args.iterations):
            selected_tasks = random.sample(task_ids, min(args.tasks_per_session, len(task_ids)))
            for task_id in selected_tasks:
                scenario = scenario_results[task_id]
                args_list.append((i + 1, task_id, scenario, args.browserless_url, provider_api_key))
        
        # Run stress test with multiprocessing
        test_results = []
        with ProcessPoolExecutor(max_workers=args.concurrent) as executor:
            future_to_args = {executor.submit(complete_task_worker, args_tuple): args_tuple for args_tuple in args_list}
            
            for future in as_completed(future_to_args):
                args_tuple = future_to_args[future]
                session_index = args_tuple[0]
                try:
                    result = future.result()
                    test_results.append(result)
                    print(f"Completed session {session_index}: {'Success' if result.success else 'Failed'}")
                except Exception as e:
                    print(f"Session {session_index} failed with exception: {e}")
                    failed_result = TestResult(
                        session_id=str(uuid.uuid4()),
                        task_id=args_tuple[1],
                        scenario=args_tuple[2].value,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        success=False,
                        error_message=str(e)
                    )
                    test_results.append(failed_result)
        
        # Calculate results
        successful_count = len([r for r in test_results if r.success])
        failed_count = len([r for r in test_results if not r.success])
        hotlabel_modals_found = len([r for r in test_results if r.hotlabel_modal_found])
        hotlabel_tasks_completed = sum([r.hotlabel_tasks_completed for r in test_results])
        
        # Print results
        end_time = datetime.utcnow()
        print("\n" + "=" * 80)
        print("Headless Stress Test Results (Multiprocessing)")
        print("=" * 80)
        
        print(f"Test Duration: {end_time - start_time}")
        print(f"Total Sessions: {args.iterations}")
        print(f"Successful: {successful_count}")
        print(f"Failed: {failed_count}")
        print(f"Success Rate: {(successful_count / len(test_results) * 100):.2f}%")
        print(f"HotLabel Modals Found: {hotlabel_modals_found}")
        print(f"HotLabel Tasks Completed: {hotlabel_tasks_completed}")
        
        # Save results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"headless_stress_test_mp_results_{timestamp}.json"
        
        results_data = {
            "test_config": {
                "iterations": args.iterations,
                "concurrent": args.concurrent,
                "tasks_per_session": args.tasks_per_session,
                "browserless_url": args.browserless_url
            },
            "test_duration": str(end_time - start_time),
            "results": {
                "total_sessions": args.iterations,
                "successful": successful_count,
                "failed": failed_count,
                "success_rate": (successful_count / len(test_results) * 100),
                "hotlabel_modals_found": hotlabel_modals_found,
                "hotlabel_tasks_completed": hotlabel_tasks_completed
            },
            "test_results": [asdict(r) for r in test_results],
            "provider_id": provider_id,
            "task_ids": task_ids
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        print(f"\nResults saved to: {filename}")
        
    except Exception as e:
        print(f"Headless stress test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Set multiprocessing start method for macOS compatibility
    if sys.platform == "darwin":
        mp.set_start_method('spawn', force=True)
    
    main() 